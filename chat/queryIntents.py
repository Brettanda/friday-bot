import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3' 
import nltk,logging
try:
  nltk.data.find('tokenizers/punkt.zip')
except LookupError:
  nltk.download('punkt')
try:
  nltk.data.find('vader_lexicon')
except LookupError:
  nltk.download('vader_lexicon')
from nltk.sentiment import SentimentIntensityAnalyzer
sia = SentimentIntensityAnalyzer()
from nltk.stem.lancaster import LancasterStemmer
stemmer = LancasterStemmer()
# things we need for Tensorflow
import numpy as np
from keras.models import Sequential, load_model
from keras.layers import Dense, Activation, Dropout
from keras.optimizers import SGD
import pandas as pd
import random

words = []
classes = []
documents = []
ignore_words = ['?']
context = []
# loop through each sentence in our intents patterns

model = load_model("ml/models/intent_model.h5")

import json
with open("ml/intents.json",encoding="utf8") as f:
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

def clean_up_sentence(sentence):
  # tokenize the pattern - split words into array
  sentence_words = nltk.word_tokenize(sentence)
  # stem each word - create short form for word
  sentence_words = [stemmer.stem(word.lower()) for word in sentence_words]
  return sentence_words

# return bag of words array: 0 or 1 for each word in the bag that exists in the sentence
def bow(sentence, words, show_details=True):
  # tokenize the pattern
  sentence_words = clean_up_sentence(sentence)
  # bag of words - matrix of N words, vocabulary matrix
  bag = [0]*len(words)  
  inbag = ""
  for s in sentence_words:
    for i,w in enumerate(words):
      if w == s: 
        # assign 1 if current word is in the vocabulary position
        bag[i] = 1
        if show_details:
          inbag += f"{w} "
          # print ("found in bag: %s" % w)
  # print(f"found in bag: {inbag}")
  # logging.info(f"found in bag: {inbag}")
  return(np.array(bag),inbag)

async def classify_local(sentence):
  ERROR_THRESHOLD = 0.7
  
  # generate probabilities from the model
  bows,inbag = bow(sentence, words)
  input_data = pd.DataFrame([bows], dtype=float, index=['input'])
  # print(inbag)
  results = model.predict([input_data])[0]
  # filter out predictions below a threshold, and provide intent index
  # guesses = [[i,r] for i,r in enumerate(results) if r>ERROR_THRESHOLD/2]
  results = [[i,r] for i,r in enumerate(results) if r>ERROR_THRESHOLD]
  # sort by strength of probability
  results.sort(key=lambda x: x[1], reverse=True)
  # guesses.sort(key=lambda x: x[1], reverse=True)
  return_list = []
  for r in results:
    return_list.append((r[0],classes[r[0]], str(r[1])))
  # return tuple of intent and probability
  # guess_list = []
  # for r in guesses:
  #   guess_list.append((r[0],classes[r[0]], str(r[1])))

  if len(return_list) > 0:
    index,name,chance = return_list[0]
    tag = [index for index,value in enumerate(intents) if value["tag"] == name]
    intent = intents[tag[0]]
    # guess_index,guess_name,guess_chance = guess_list[0]
    # guess_tag = [guess_index for index,value in enumerate(intents) if value["tag"] == name]
    # guess_intent = intents[guess_tag[0]]
    print(return_list)
    # print(chance)
    # logging.info(chance)

    if isinstance(intent["responses"],list) and len(intent["responses"]) > 0:
      indresp = random.randint(0,len(intent["responses"]) - 1)

      response = intent["responses"][indresp]
      # print(intent["incomingContext"],intent["outgoingContext"])
      # print(len(intent["incomingContext"]),len(intent["outgoingContext"]))
      return response,intent["tag"],chance,inbag,intent["incomingContext"],intent["outgoingContext"],sia.polarity_scores(sentence)
    else:
      return None,None,None,None,None,None,None
  else:
    return None,None,None,None,None,None,None
