import { connect } from 'react-redux';
import React from 'react';

import { setIsBatchView } from '../actions';

class NavigationBar extends React.Component {
  render() {
    let totalItems = this.props.unlabelled + this.props.labelled.total;
    let labelled = this.props.labelled.total;
    let maxAccuracy = 0;
    if (this.props.history.length > 1) {
      maxAccuracy = Math.round(
        Math.max(...this.props.history.map((step) => step['test']['acc'])) * 100
      )
    }

    let toggleBatchView = null;
    // TODO: Turn this on again when batch view is ready.
    if (this.props.task.dataType === 'images' &&
      (this.props.task.labelType === 'binary' ||
      this.props.task.labelType === 'classification')) {
      toggleBatchView = (
        <div className="btn-group btn-group-toggle" data-toggle="buttons">
          <label onClick={this.props.onClickSingle} className={this.props.task.isBatchView ? "btn btn-secondary active" : "btn btn-secondary"}>
            <input type="radio" name="options" autocomplete="off" checked /> Single
          </label>
          <label onClick={this.props.onClickBatch} className={this.props.task.isBatchView ? "btn btn-secondary" : "btn btn-secondary active"}>
            <input type="radio" name="options" autocomplete="off" /> Batch
          </label>
        </div>
      );
    }
    let isTraining = null;
    if (this.props.labelled.train > this.props.task.minTrain) {
      isTraining = (<span className="text-success">Yes</span>)
    } else {
      isTraining = (<span className="text-danger">No</span>)
    }

    return (
      <nav className="navbar navbar-toggleable-md navbar-light bg-faded navbar-expand-md">
        <button className="navbar-toggler navbar-toggler-right" type="button" data-toggle="collapse" data-target="#navbarNavAltMarkup" aria-controls="navbarNavAltMarkup" aria-expanded="false" aria-label="Toggle navigation">
          <span className="navbar-toggler-icon"></span>
        </button>
        <a className="navbar-brand" href="#"><i className="far fa-lightbulb"></i></a>
        <div className="collapse navbar-collapse" id="navbarNavAltMarkup">
          <div className="navbar-nav">
            <a className="nav-item nav-link">Labelled: <b id="labelled-counts-text">{labelled} / {totalItems}</b></a>
            <a className="nav-item nav-link">Accuracy: <b id="accuracy-text">{maxAccuracy}%</b></a>
            <a className="nav-item nav-link">Training: <b id="accuracy-text">{isTraining}</b></a>
          </div>
        </div>
      </nav>
    );
  }
}

const mapStateToProps = state => ({
  task: state.task,
  unlabelled: state.stats.unlabelled,
  labelled: state.stats.labelled,
  history: state.stats.history,
  errorMsg: state.judgements.errorMsg || state.stats.errorMsg || state.items.errorMsg,
  fetching: state.judgements.fetching || state.stats.fetching || state.items.fetching,
});


const mapDispatchToProps = dispatch => ({
  onClickBatch: (e) => {
    e.preventDefault();
    dispatch(setIsBatchView(true));
  },
  onClickSingle: (e) => {
    e.preventDefault();
    dispatch(setIsBatchView(false));
  },
});

export default connect(
  mapStateToProps,
  mapDispatchToProps,
)(NavigationBar);
