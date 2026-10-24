import tempfile
from app.experiment_store import ExperimentStore, ExperimentNotFound


def test_experiment_persists_across_store_instances():
    db = tempfile.mktemp(suffix=".db")
    store1 = ExperimentStore(db)
    created = store1.create("exp-1", "hadamard_all", 2, 32)
    store1.update("exp-1", status="completed", result={"counts": {"00": 16, "11": 16}})
    store2 = ExperimentStore(db)
    fetched = store2.get("exp-1")
    assert fetched["status"] == "completed"
    assert fetched["result"]["counts"]["00"] == 16


def test_list_experiments_limit():
    db = tempfile.mktemp(suffix=".db")
    store = ExperimentStore(db)
    store.create("exp-a", "hadamard_all", 1, 8)
    store.create("exp-b", "hadamard_all", 1, 8)
    assert len(store.list(1)) == 1


def test_unknown_experiment_raises():
    store = ExperimentStore(tempfile.mktemp(suffix=".db"))
    try:
        store.get("missing")
    except ExperimentNotFound:
        pass
    else:
        raise AssertionError("missing experiment should raise")
