import json
import os
# import pickle
import random

import nltk
import numpy as np
# import pandas as pd
from keras.layers import Dense, Dropout  # , Activation
from keras.models import Sequential
from keras.optimizers import SGD
from nltk.stem.lancaster import LancasterStemmer

stemmer = LancasterStemmer()
os.add_dll_directory("C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v10.1\\bin")
os.add_dll_directory("C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v10.1\\libnvvp")
os.add_dll_directory("C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v10.1")
os.add_dll_directory("C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v10.1\\extras\\CUPTI\\lib64")
os.add_dll_directory("C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v10.1\\include")
os.add_dll_directory("C:\\tools\\cuda\\bin")
os.add_dll_directory("C:\\tools\\cuda")
os.add_dll_directory("C:\\Program Files\\NVIDIA Corporation\\Nsight Compute 2019.4.0")

words = []
classes = []
documents = []
ignore_words = ['?']
# loop through each sentence in our intents patterns

with open("ml/intents.json", encoding="utf8") as f:
  intents = json.load(f)

new = []
for intent in intents:
  if int(intent["priority"]) > 0:
    new.append(intent)

intents = new

for intent in intents:
  for pattern in intent['patterns']:
    # tokenize each word in the sentence
    w = nltk.word_tokenize(pattern)
    # add to our words list
    words.extend(w)
    # add to documents in our corpus
    documents.append((w, intent['tag']))
    # add to our classes list
    if intent['tag'] not in classes:
      classes.append(intent['tag'])
# stem and lower each word and remove duplicates
words = [stemmer.stem(w.lower()) for w in words if w not in ignore_words]
words = sorted(list(set(words)))
# sort classes
# classes = list(set(classes))
classes = sorted(list(set(classes)))
# documents = combination between patterns and intents
# print (len(documents), "documents")
# # classes = intents
# print (len(classes), "classes", classes)
# # words = all words, vocabulary
# print (len(words), "unique stemmed words", words)

# create our training data
training = []
# create an empty array for our output
output_empty = [0] * len(classes)
# training set, bag of words for each sentence
for doc in documents:
  # initialize our bag of words
  bag = []
  # list of tokenized words for the pattern
  pattern_words = doc[0]
  # stem each word - create base word, in attempt to represent related words
  pattern_words = [stemmer.stem(word.lower()) for word in pattern_words]
  # create our bag of words array with 1, if word match found in current pattern
  for w in words:
    bag.append(1) if w in pattern_words else bag.append(0)

  # output is a '0' for each tag and '1' for current tag (for each pattern)
  output_row = list(output_empty)
  output_row[classes.index(doc[1])] = 1

  training.append([bag, output_row])
# shuffle our features and turn into np.array
random.shuffle(training)
training = np.array(training)
# create train and test lists. X - patterns, Y - intents
train_x = list(training[:, 0])
train_y = list(training[:, 1])

# Create model - 3 layers. First layer 128 neurons, second layer 64 neurons and 3rd output layer contains number of neurons
# equal to number of intents to predict output intent with softmax
model = Sequential()
# model.add(Dense(256, input_shape=(len(train_x[0]),), activation='relu'))
model.add(Dense(128, input_shape=(len(train_x[0]),), activation='relu'))
model.add(Dropout(0.25))
# model.add(Dense(128, activation='relu'))
# model.add(Dropout(0.25))
model.add(Dense(64, activation='relu'))
model.add(Dropout(0.25))
model.add(Dense(len(train_y[0]), activation='softmax'))

# Compile model. Stochastic gradient descent with Nesterov accelerated gradient gives good results for this model
sgd = SGD(lr=0.01, decay=1e-6, momentum=0.9, nesterov=True)
model.compile(loss='categorical_crossentropy', optimizer=sgd, metrics=['accuracy'])
# model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])

# Fit the model
model.fit(np.array(train_x), np.array(train_y), epochs=200, batch_size=5, verbose=1, shuffle=True)
model.summary()

model.save('ml/models/intent_model.h5')
