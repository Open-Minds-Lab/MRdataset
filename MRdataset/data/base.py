from abc import ABC, abstractmethod


class Dataset(ABC):
    """This class is an abstract base class (ABC) for datasets.

    To create a subclass, you need to implement the following functions:
    -- <__init__>:      initialize the class, first call super().__init__()
    -- <__getitem__>:   get a data sample
    """
    def __init__(self, **kwargs):
        """
        Initialize the class; save the options in the class
        """
        self.name = None

    @abstractmethod
    def __getitem__(self, *args, **kwargs):
        raise NotImplementedError("__getitem__ attribute implementation for dataset is missing.")

    @abstractmethod
    def __len__(self):
        raise TypeError("__len__ attribute implementation for dataset is missing.")





