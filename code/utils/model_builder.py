from dataset import Dataset
from label import Label
from models.cnn_model import CNNModel
from models.rnn_model import RNNModel
from models.sequence_model import SequenceModel
from models.stub_model import StubModel
from models.lightnet_model import LightnetModel

class ModelBuilder:
    def __init__(self, dataset, label):
        self.dataset = dataset
        self.label = label

    def build(self):
        # Right now there is an assumption that
        if self.dataset.data_type == Dataset.IMAGE_TYPE and self.label.label_type == Label.BINARY:
            return CNNModel(input_shape=(128, 128))
        if self.dataset.data_type == Dataset.OBJECT_DETECTION_TYPE and self.label.label_type == Label.OBJECT_DETECTION:
            return LightnetModel()
        if self.dataset.data_type == Dataset.TEXT_TYPE and self.label.label_type == Label.BINARY:
            return RNNModel()
        if self.dataset.data_type == Dataset.TEXT_TYPE and self.label.label_type == Label.SEQUENCE:
            return SequenceModel(
                valid_outputs=self.label.valid_tokens,
                seq2seq=False,
                character_mode=False,
            )

        return StubModel()
