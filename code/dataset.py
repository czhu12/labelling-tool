import pandas as pd
import os
import glob
from utils import utils
import chardet
from utils import glove_utils
from threading import Lock

import copy
import logging
import json
from PIL import Image
from brambox.boxes.annotations import Annotation
import lightnet.data as lnd
from typing import List

MIN_TRAIN_EXAMPLES = 10
MIN_TEST_EXAMPLES = 20
MIN_UNSUPERVISED_EXAMPLES = 100


class Dataset:
    TRAIN = 'TRAIN'
    TEST = 'TEST'
    MODEL_LABELLED = 'MODEL_LABELLED'
    IMAGE_TYPE = 'images'
    TEXT_TYPE = 'text'
    OBJECT_DETECTION_TYPE = 'object_detection'

    @staticmethod
    def load_from(config):
        if config['data_type'] == Dataset.IMAGE_TYPE:
            return ImageDataset(config)
        elif config['data_type'] == Dataset.TEXT_TYPE:
            return TextDataset(config)
        elif config['data_type'] == Dataset.OBJECT_DETECTION_TYPE:
            return ObjectDetectionDataset(config)
        else:
            pass

    def __init__(self, config):
        self.data_type = config.get('data_type')
        self.directory = config.get('directory')
        self.judgements_file = config.get('judgements_file')
        self.save_lock = Lock()

        # Start dataset with existing judgements
        self.dataset = self.load_existing_judgements()
        # Add unlabelled examples
        unlabelled = self.load_unlabelled_dataset()

        self.dataset = self.dataset.append(unlabelled)
        self.loaded_text = False
        self.current_stage = Dataset.TEST

    def save(self):
        self.save_lock.acquire()
        try:
            directory = os.path.dirname(self.judgements_file)
            if not os.path.exists(directory):
                os.makedirs(directory)
            # Make directory if it doesn't exist
            self.labelled.to_csv(self.judgements_file, index=False)
        finally:
            self.save_lock.release()

    @property
    def stats(self):
        return {
            "labelled": {
                "total": len(self.labelled),
                "train": len(self.train_data),
                "model_labelled": len(self.model_labelled_data),
                "test": len(self.test_data),
            },
            "unlabelled": len(self.unlabelled),
        }

    def load_unlabelled_dataset(self):
        raise NotImplementedError

    def empty_dataframe(self):
        df = pd.DataFrame(columns=self.__class__.COLUMNS)
        return df

    def load_existing_judgements(self):
        if not os.path.isfile(self.judgements_file):
            return self.empty_dataframe()

        df = pd.read_csv(self.judgements_file)
        assert sorted(df.columns) == sorted(self.__class__.COLUMNS)
        df['labelled'] = True
        return df

    @property
    def unlabelled(self):
        return self.dataset[self.dataset['labelled'] == False]

    @property
    def labelled(self):
        return self.dataset[self.dataset['labelled'] == True]

    @property
    def model_labelled_data(self):
        return self.labelled[self.labelled['stage'] == Dataset.MODEL_LABELLED]

    @property
    def train_data(self):
        return self.labelled[self.labelled['stage'] == Dataset.TRAIN]

    @property
    def test_data(self):
        return self.labelled[self.labelled['stage'] == Dataset.TEST]

    def sample(self, size=100):
        if len(self.unlabelled) < size:
            return self.unlabelled
        return self.unlabelled.sample(size)

    @property
    def train_set(self):
        raise NotImplementedError

    def unlabelled_set(self):
        raise NotImplementedError

    def set_current_stage(self):
        if len(self.test_data) <= MIN_TEST_EXAMPLES:
            self.current_stage = Dataset.TEST
            return

        ratio = len(self.test_data) / (len(self.train_data) + 1)

        if ratio < 0.33:
            self.current_stage = Dataset.TEST
        else:
            self.current_stage = Dataset.TRAIN

    @property
    def test_set(self):
        raise NotImplementedError

    def add_label(self, id, label, stage, user='default'):
        self.dataset.loc[self.dataset['path'] == id, ['label', 'labelled', 'stage', 'labelled_by']] = [label, True, stage, user]
        self.save()

    def get_data(self, _id):
        return None

class TextDataset(Dataset):
    COLUMNS = ['label', 'labelled_by', 'path', 'labelled', 'stage', 'text']

    def get_data(self, _id):
        return self.dataset[self.dataset['path'] == _id]['text'].values[0]

    def load_unlabelled_dataset(self):
        types = ['*.txt']
        text_paths = []
        for type in types:
            text_paths.extend(glob.glob("{}/{}".format(self.directory, type)))

        if len(set(text_paths)) == 0:
            raise ValueError("No txt files found in {}. Probably pointing at a wrong directory?".format(self.directory))

        unlabelled_paths = set(text_paths) - set(self.dataset['path'].values)
        data = []
        for path in unlabelled_paths:
            data.append({
                'path': path,
                'labelled': False,
                'text': open(path).read(),
            })
        new_dataset = pd.DataFrame(
            data,
            columns=self.__class__.COLUMNS,
        )
        return new_dataset

    @property
    def test_set(self):
        if len(self.test_data) == 0:
            return [], []

        test_data = self.test_data
        x_train = test_data['text'].values
        y_train = test_data['label'].values
        return x_train, y_train

    @property
    def train_set(self):
        if len(self.train_data) == 0:
            return [], []
        train_data = self.train_data
        x_train = train_data['text'].values
        y_train = train_data['label'].values
        return x_train, y_train

    def unlabelled_set(self, size=MIN_UNSUPERVISED_EXAMPLES):
        data = self.sample(size)
        return data['text'].values, data['path'].values

class ImageDataset(Dataset):
    COLUMNS = ['label', 'labelled_by', 'path', 'labelled', 'stage']

    def __init__(self, config):
        super(ImageDataset, self).__init__(config)
        if 'image_width' in config and 'image_height' in config:
            self.input_shape = (int(config['image_width']), int(config['image_height']))
        else:
            self.input_shape = (128, 128)

    def load_unlabelled_dataset(self):
        types = ['*.jpg', '*.png']
        image_paths = []
        for type in types:
            image_paths.extend(glob.glob("{}/{}".format(self.directory, type)))

        if len(set(image_paths)) == 0:
            raise ValueError(
                "No jpg or png files found in {}. Probably pointing at a wrong directory?".format(directory),
            )
        unlabelled_paths = set(image_paths) - set(self.dataset['path'].values)
        new_dataset = pd.DataFrame([{'path': path, 'labelled': False} for path in unlabelled_paths], columns=self.__class__.COLUMNS)
        return new_dataset

    @property
    def test_set(self):
        if len(self.test_data) == 0:
            return [], []
        test_data = self.test_data
        x_train = utils.load_images(test_data['path'].values, self.input_shape)
        y_train = utils.one_hot_encode(test_data['label'].values)
        return x_train, y_train

    @property
    def train_set(self):
        if len(self.train_data) == 0:
            return [], []
        train_data = self.train_data
        x_train = utils.load_images(train_data['path'].values, self.input_shape)
        y_train = utils.one_hot_encode(train_data['label'].values)
        return x_train, y_train

    def unlabelled_set(self, size=MIN_UNSUPERVISED_EXAMPLES):
        data = self.sample(size)
        if len(data) > 0:
            x_train = utils.load_images(data['path'].values, self.input_shape)
            ids = data['path'].values
        else:
            x_train = []
            ids = []
        return x_train, ids


# Object detection
def serialize_brambox(box) -> str:
    return json.dumps({
        'class_label': box.class_label,
        'object_id': box.object_id,
        'x_top_left': box.x_top_left,
        'y_top_left': box.y_top_left,
        'width': box.width,
        'height': box.height,
    })

def deserialize_bramboxes(encoding: str) -> List[Annotation]:
    boxes = json.loads(encoding)
    return [deserialize_brambox(box) for box in boxes]

def deserialize_brambox(obj: str) -> Annotation:
    box = Annotation()
    box.class_label = obj['class_label']
    box.object_id = 0
    box.x_top_left = obj['x_top_left']
    box.y_top_left = obj['y_top_left']
    box.width = obj['width']
    box.height = obj['height']
    return box

class ObjectDetectionDataset(ImageDataset):
    @property
    def test_set(self):
        if len(self.test_data) == 0:
            return [], []
        test_data = self.test_data
        paths = train_data['path'].values
        boxes = [deserialize_bramboxes(label) for label in train_data['label'].values]
        return paths, boxes

    @property
    def train_set(self):
        if len(self.train_data) == 0:
            return [], []
        train_data = self.train_data
        paths = train_data['path'].values
        boxes = [deserialize_bramboxes(label) for label in train_data['label'].values]
        return paths, boxes
