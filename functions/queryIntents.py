# import json
# # import logging
# import os
# import random

# import nltk  # type: ignore
# import numpy as np
# import pandas as pd
# # from tensorflow.keras.optimizers import SGD
# from nltk.sentiment import SentimentIntensityAnalyzer  # type: ignore
# # from nltk.stem.lancaster import LancasterStemmer
# from nltk.stem import PorterStemmer  # type: ignore
# from spellchecker import SpellChecker  # type: ignore
# # from flair.data import Sentence
# # from flair.models import MultiTagger  # , SequenceTagger
# # from tensorflow.keras.layers import Dropout, Activation, Dense
# from tensorflow.keras.models import load_model  # type: ignore

# spell = SpellChecker()

# try:
#   nltk.data.find('tokenizers/punkt.zip')
# except LookupError:
#   nltk.download('punkt')
# try:
#   nltk.data.find('vader_lexicon')
# except LookupError:
#   nltk.download('vader_lexicon')
# sia = SentimentIntensityAnalyzer()
# stemmer = PorterStemmer()
# os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

# # tagger = MultiTagger.load(["pos","ner"])

# words = []
# classes = []
# documents = []
# ignore_words = ['?', '.', ',', '!']
# context = []
# # loop through each sentence in our intents patterns

# model = load_model("ml/models/intent_model.h5")


# with open("spice/ml/intents-toyst.json", encoding="utf8") as f:
#   intents = json.load(f)

# for intent in intents:
#   for pattern in intent['patterns']:
#     # tokenize each word in the sentence
#     w = nltk.word_tokenize("".join([p["text"] for p in pattern]))
#     # add to our words list
#     words.extend(w)
#     # add to documents in our corpus
#     documents.append((w, intent['tag']))
#     # add to our classes list
#     if intent['tag'] not in classes:
#       classes.append(intent['tag'])
# # stem and lower each word and remove duplicates
# words = [stemmer.stem(w.lower()) for w in words if w not in ignore_words]
# words = sorted(list(set(words)))
# # sort classes
# # classes = list(set(classes))
# classes = sorted(list(set(classes)))


# def clean_up_sentence(sentence):
#   # tokenize the pattern - split words into array
#   sentence_words = nltk.word_tokenize(sentence)
#   # stem each word - create short form for word
#   sentence_words = [stemmer.stem(word.lower()) for word in sentence_words]
#   return sentence_words

# # return bag of words array: 0 or 1 for each word in the bag that exists in the sentence


# def bow(sentence, wrds, show_details=True, mentioned=False):
#   # tokenize the pattern
#   sentence_words = clean_up_sentence(sentence)
#   x = 0
#   for word in sentence_words:
#     corrected_word = spell.correction(word)
#     if word == "r":
#       sentence_words[x] = "are"
#     elif word == "u":
#       sentence_words[x] = "you"
#     elif word != corrected_word:
#       sentence_words[x] = corrected_word
#     x += 1
#   # bag of words - matrix of N words, vocabulary matrix
#   bag = [0] * len(wrds)
#   inbag = ""
#   for s in sentence_words:
#     for i, w in enumerate(wrds):
#       if w == s:
#         # assign 1 if current word is in the vocabulary position

#         bag[i] = 1
#         if show_details:
#           inbag += f"{w} "
#           # print ("found in bag: ?" % w)
#   # sentiment = sia.polarity_scores(" ".join(sentence))
#   # bag.insert(0, sentiment["neg"])
#   # bag.insert(0, sentiment["neu"])
#   # bag.insert(0, sentiment["pos"])
#   # bag.insert(0, 1 if "friday" in sentence else 0)
#   # bag.insert(0, sentiment["compound"])
#   # bag.insert(0, 0)
#   # print(f"found in bag: {inbag}")
#   # logging.info(f"found in bag: {inbag}")
#   return (np.array(bag), inbag)


# async def classify_local(sentence, mentioned=False):
#   ERROR_THRESHOLD = 0.8

#   # generate probabilities from the model
#   bows, inbag = bow(sentence, words, mentioned=mentioned)
#   input_data = pd.DataFrame([bows], dtype=float, index=['input'])
#   # print(inbag)
#   results = model.predict([input_data])[0]
#   # filter out predictions below a threshold, and provide intent index
#   # guesses = [[i, r] for i, r in enumerate(results) if r > ERROR_THRESHOLD / 2]
#   results = [[i, r] for i, r in enumerate(results) if r > ERROR_THRESHOLD]
#   # sort by strength of probability
#   results.sort(key=lambda x: x[1], reverse=True)
#   # guesses.sort(key=lambda x: x[1], reverse=True)
#   return_list = []
#   for r in results:
#     return_list.append((r[0], classes[r[0]], str(r[1])))
#   # return tuple of intent and probability
#   # guess_list = []
#   # for r in guesses:
#   #   guess_list.append((r[0], classes[r[0]], str(r[1])))

#   # text = Sentence(sentence)
#   # tagger.predict(text)
#   # for entity in text.get_spans('pos'):
#   #   print(entity)
#   # for entity in text.get_spans('ner'):
#   #   print(entity)

#   if len(return_list) > 0:
#     name, chance = return_list[0][1:]
#     tag = [index for index, value in enumerate(intents) if value["tag"] == name]
#     intent = intents[tag[0]]
#     # guess_index,guess_name,guess_chance = guess_list[0]
#     # guess_tag = [guess_index for index,value in enumerate(intents) if value["tag"] == name]
#     # guess_intent = intents[guess_tag[0]]
#     print(return_list)
#     # print(chance)
#     # logging.info(chance)

#     if isinstance(intent["responses"], list) and len(intent["responses"]) > 0:
#       indresp = random.randint(0, len(intent["responses"]) - 1)

#       response = intent["responses"][indresp]
#       # print(intent["incomingContext"],intent["outgoingContext"])
#       # print(len(intent["incomingContext"]),len(intent["outgoingContext"]))
#       return response, intent["tag"], chance, inbag, intent["incomingContext"], intent["outgoingContext"], sia.polarity_scores(sentence)
#     else:
#       return None, None, None, None, None, None, None
#   else:
#     return None, None, None, None, None, None, None
