from flair.models.text_classification_model import TARSClassifier
from flair.trainers import ModelTrainer
from flair.datasets import SentenceDataset
from flair.data import Corpus, Sentence, Span
import os
os.add_dll_directory("C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v11.0\\bin")
os.add_dll_directory("C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v11.0\\libnvvp")
os.add_dll_directory("C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v11.0")
os.add_dll_directory("C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v11.0\\extras\\CUPTI\\lib64")
os.add_dll_directory("C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v11.0\\include")
os.add_dll_directory("C:\\tools\\cuda\\bin")
os.add_dll_directory("C:\\tools\\cuda")
os.add_dll_directory("C:\\Program Files\\NVIDIA Corporation\\Nsight Compute 2019.4.0")


train = SentenceDataset(
    [
        Span(Sentence("what is 1+1")).add_label("math", "1+1"),
        Span(Sentence("do you know the answer to (2*50)+6-2")).add_label("math", "1+1")
    ]
)

test = SentenceDataset(
    [
        Span(Sentence("can i get the answer for 2+2")).add_label("math", "1+1"),
    ]
)

corpus = Corpus(train=train, test=test)


tars = TARSClassifier.load('tars-base')

# tars =
