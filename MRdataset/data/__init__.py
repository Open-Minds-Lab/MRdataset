import importlib
from MRdataset.data import base


def find_dataset_using_style(dataset_style):
    """
    Import the module "data/{style}_dataset.py", which will instantiate
    {Style}Dataset(). For future, please ensure that any {Style}Dataset
    is a subclass of MRdataset.base.Dataset
    """

    dataset_modulename = "MRdataset.data." + dataset_style + "_dataset"
    datasetlib = importlib.import_module(dataset_modulename)

    dataset = None
    target_dataset_class = dataset_style+'dataset'
    for name, cls in datasetlib.__dict__.items():
        if name.lower() == target_dataset_class.lower() \
                and issubclass(cls, base.Dataset):
            dataset = cls

    if dataset is None:
        raise NotImplementedError("Expected to find %s which is supposed  \
        to be a subclass of base.Dataset in %s.py" % (target_dataset_class, dataset_modulename))

    return dataset
