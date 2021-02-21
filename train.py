custom = False

import os
os.add_dll_directory("C:\Program Files\\NVIDIA GPU Computing Toolkit\CUDA\\v11.0\\bin")
os.add_dll_directory("C:\Program Files\\NVIDIA GPU Computing Toolkit\CUDA\\v11.0\\libnvvp")
os.add_dll_directory("C:\Program Files\\NVIDIA GPU Computing Toolkit\CUDA\\v11.0")
os.add_dll_directory("C:\Program Files\\NVIDIA GPU Computing Toolkit\CUDA\\v11.0\\extras\\CUPTI\\lib64")
os.add_dll_directory("C:\Program Files\\NVIDIA GPU Computing Toolkit\CUDA\\v11.0\\include")
os.add_dll_directory("C:\\tools\\cuda\\bin")
os.add_dll_directory("C:\\tools\\cuda")
os.add_dll_directory("C:\Program Files\\NVIDIA Corporation\\Nsight Compute 2019.4.0")
import re
import random
if custom == True:
  data_path = "ml/custom_human_text.txt"
  data_path2 = "ml/custom_robot_text.txt"
else:
  data_path = "ml/human_text.txt"
  data_path2 = "ml/robot_text.txt"
# Defining lines as a list of each line
with open(data_path, 'r', encoding='utf-8') as f:
  lines = f.read().split('\n')
with open(data_path2, 'r', encoding='utf-8') as f:
  lines2 = f.read().split('\n')
lines = [re.sub(r"\[\w+\]",'hi',line) for line in lines]
lines = [" ".join(re.findall(r"\w+",line)) for line in lines]
lines2 = [re.sub(r"\[\w+\]",'',line) for line in lines2]
lines2 = [" ".join(re.findall(r"\w+",line)) for line in lines2]
# grouping lines by response pair
pairs = list(zip(lines,lines2))
# random.shuffle(pairs)


import numpy as np
from tensorflow import keras
from keras.layers import Input, LSTM, Dense, Reshape
from keras.models import Model, load_model
from keras.callbacks import ModelCheckpoint
def start(pairss):
  input_docs = []
  target_docs = []
  input_tokens = set()
  target_tokens = set()
  if custom == False:
    pairss = pairss[:800]
  for line in pairss:
  # for line in pairs[:1500]:
    input_doc, target_doc = line[0], line[1]
    # Appending each input sentence to input_docs
    input_docs.append(input_doc)
    # Splitting words from punctuation  
    target_doc = " ".join(re.findall(r"[\w']+|[^\s\w]", target_doc))
    # Redefine target_doc below and append it to target_docs
    target_doc = '<START> ' + target_doc + ' <END>'
    target_docs.append(target_doc)
    
    # Now we split up each sentence into words and add each unique word to our vocabulary set
    for token in re.findall(r"[\w']+|[^\s\w]", input_doc):
      if token not in input_tokens:
        input_tokens.add(token)
    for token in target_doc.split():
      if token not in target_tokens:
        target_tokens.add(token)
  input_tokens = sorted(list(input_tokens))
  target_tokens = sorted(list(target_tokens))
  num_encoder_tokens = len(input_tokens)
  num_decoder_tokens = len(target_tokens)

  input_features_dict = dict(
      [(token, i) for i, token in enumerate(input_tokens)])
  target_features_dict = dict(
      [(token, i) for i, token in enumerate(target_tokens)])
  reverse_input_features_dict = dict(
      (i, token) for token, i in input_features_dict.items())
  reverse_target_features_dict = dict(
      (i, token) for token, i in target_features_dict.items())


  #Maximum length of sentences in input and target documents
  max_encoder_seq_length = max([len(re.findall(r"[\w']+|[^\s\w]", input_doc)) for input_doc in input_docs])
  max_decoder_seq_length = max([len(re.findall(r"[\w']+|[^\s\w]", target_doc)) for target_doc in target_docs])
  encoder_input_data = np.zeros(
      (len(input_docs), max_encoder_seq_length, num_encoder_tokens),
      dtype='float32')
  decoder_input_data = np.zeros(
      (len(input_docs), max_decoder_seq_length, num_decoder_tokens),
      dtype='float32')
  decoder_target_data = np.zeros(
      (len(input_docs), max_decoder_seq_length, num_decoder_tokens),
      dtype='float32')
  for line, (input_doc, target_doc) in enumerate(zip(input_docs, target_docs)):
      for timestep, token in enumerate(re.findall(r"[\w']+|[^\s\w]", input_doc)):
          #Assign 1. for the current line, timestep, & word in encoder_input_data
          encoder_input_data[line, timestep, input_features_dict[token]] = 1.
      
      for timestep, token in enumerate(target_doc.split()):
          decoder_input_data[line, timestep, target_features_dict[token]] = 1.
          if timestep > 0:
              decoder_target_data[line, timestep - 1, target_features_dict[token]] = 1.
  #Dimensionality
  dimensionality = 256
  #The batch size and number of epochs
  batch_size = 3
  epochs = 20
  #Encoder
  encoder_inputs = Input(shape=(None, num_encoder_tokens))
  # encoder_inputs = Input(shape=(None, len(pairs)))
  encoder_lstm = LSTM(dimensionality, return_state=True)
  encoder_outputs, state_hidden, state_cell = encoder_lstm(encoder_inputs)
  encoder_states = [state_hidden, state_cell]
  #Decoder
  decoder_inputs = Input(shape=(None, num_decoder_tokens))
  # decoder_inputs = Input(shape=(None, len(pairs)))
  decoder_lstm = LSTM(dimensionality, return_sequences=True, return_state=True)
  decoder_outputs, decoder_state_hidden, decoder_state_cell = decoder_lstm(decoder_inputs, initial_state=encoder_states)
  decoder_dense = Dense(num_decoder_tokens, activation='softmax')
  decoder_outputs = decoder_dense(decoder_outputs)

  del pairss
  return (encoder_input_data,decoder_input_data,decoder_target_data,encoder_inputs,decoder_inputs,decoder_outputs,num_encoder_tokens,num_decoder_tokens,epochs,batch_size)

# chunks = [":500","500:1000","1000:1500","1500:2000","2000:"]
# chunks = [[0,500],[500,1000],[1000,1500],[1500,2000],[2000,-1]]
# i = 0
# while i < len(chunks):
  # print(chunks[i])
# encoder_input_data,decoder_input_data,decoder_target_data,encoder_inputs,decoder_inputs,decoder_outputs,epochs,batch_size = start(pairs[slice(chunks[i][0],chunks[i][1])])
encoder_input_data,decoder_input_data,decoder_target_data,encoder_inputs,decoder_inputs,decoder_outputs,num_encoder_tokens,num_decoder_tokens,epochs,batch_size = start(pairs)
# if i > 0:
#   training_model = load_model("full_training_model_0.h5")
#   training_model.layers[0] = Reshape(encoder_input_data.shape)
# else:
training_model = Model([encoder_inputs, decoder_inputs], decoder_outputs)
# print(training_model.layers[0].input.reshape(encoder_input_data.shape))
# print(encoder_input_data.shape)
#Compiling
training_model.compile(optimizer='rmsprop', loss='categorical_crossentropy', metrics=['accuracy'], sample_weight_mode='temporal')
# print(encoder_input_data,decoder_input_data,decoder_target_data)
#Training
training_model.fit([encoder_input_data, decoder_input_data], decoder_target_data, batch_size = batch_size, epochs = epochs, workers=8, shuffle=True,use_multiprocessing = True) #verbose=2,   validation_split = 0.2
# training_model.build(encoder_input_data.shape)
training_model.summary()
scores = training_model.evaluate([encoder_input_data, decoder_input_data], decoder_target_data, verbose=0)
print("Accuracy: %.2f%%" % (scores[1]*100))
# training_model.save('full_training_model_0.h5')
# del encoder_input_data,decoder_input_data,decoder_target_data,encoder_inputs,decoder_inputs,decoder_outputs,epochs,batch_size
# i += 1
  

#Model
# # scores = training_model.evaluate([encoder_input_data[:500], decoder_input_data[:500]], decoder_target_data[:500], verbose=0)
# # print("Baseline Error: &.2f%%" % (100-scores[1]*100))

# training_model.save("partly_trained.h5")
# del training_model

# training_model = load_model("partly_trained.h5")

# training_model.fit([encoder_input_data[500:1000], decoder_input_data[500:1000]], decoder_target_data[500:1000], batch_size = batch_size, epochs = epochs, validation_split = 0.2, shuffle=True, use_multiprocessing = True)
# training_model.save("partly_trained-1.h5")
# filepath="weights-improvement-{epoch:02d}-{accuracy:.4f}.hdf5"
# checkpoint = ModelCheckpoint(filepath, monitor='accuracy', verbose=1, save_best_only=True, mode='min')
# callbacks_list = [checkpoint]
# training_model.fit([encoder_input_data, decoder_input_data], decoder_target_data, batch_size = batch_size, epochs = epochs, callbacks=callbacks_list, validation_split = 0.2, shuffle=True, use_multiprocessing = True)

# print(encoder_inputs)
# print(encoder_input_data)

# class MY_Generator(keras.utils.Sequence):
#     def __init__(self,encoder_input_data,decoder_input_data,decoder_target_data,batch_size):
#         self.encoder_input_data, self.decoder_input_data, self.decoder_target_data = encoder_input_data,decoder_input_data,decoder_target_data
#         self.batch_size = batch_size
#     def __len__(self):
#         return np.ceil(num_encoder_tokens / int(self.batch_size)).astype(np.int)
#     def __getitem__(self,idx):
#         batch_x = self.encoder_input_data[idx * self.batch_size:(idx + 1) * self.batch_size]
#         batch_y = self.decoder_input_data[idx * self.batch_size:(idx + 1) * self.batch_size]
#         batch_z = self.decoder_target_data[idx * self.batch_size:(idx + 1) * self.batch_size]

#         # return np.array([batch_x, batch_y], batch_z)
#         print(np.array(batch_x),np.array(batch_y),np.array(batch_z))
#         return np.array(batch_x),np.array(batch_y),np.array(batch_z)
# class MY_Generator_two(keras.utils.Sequence):
#     def __init__(self,input_data,target_data,batch_size):
#         self.input_data,self.target_data = input_data,target_data
#         self.batch_size = batch_size
#     def __len__(self):
#         return np.ceil(num_encoder_tokens / int(self.batch_size)).astype(np.int)
#     def __getitem__(self,idx):
#         batch_x = self.input_data[idx * self.batch_size:(idx + 1) * self.batch_size]
#         batch_y = self.target_data[idx * self.batch_size:(idx + 1) * self.batch_size]

#         # return np.array([batch_x, batch_y], batch_z)
#         return np.array(batch_x),np.array(batch_y)
        
# class MY_Generator(keras.utils.Sequence):
#     def __init__(self,input_data,batch_size):
#         self.input_data = input_data
#         self.batch_size = batch_size
#     def __len__(self):
#         return np.ceil(num_encoder_tokens / int(self.batch_size)).astype(np.int)
#     def __getitem__(self,idx):
#         batch_x = self.input_data[idx * self.batch_size:(idx + 1) * self.batch_size]

#         # return np.array([batch_x, batch_y], batch_z)
#         return np.array(batch_x)

# my_training_batch_generator_encoder_input_data = MY_Generator_two(encoder_input_data,decoder_input_data,batch_size)
# my_training_batch_generator_decoder_target_data = MY_Generator(decoder_target_data,batch_size)

# # print(my_training_batch_generator)
# training_model.summary()
# training_model.fit(my_training_batch_generator_encoder_input_data,my_training_batch_generator_decoder_target_data, verbose = 1, epochs = epochs, shuffle=True, use_multiprocessing = True, max_queue_size=32)
if custom == True:
  training_model.save('ml/models/custom_gen_model.h5')
else:
  training_model.save('ml/models/gen_model.h5')


# training_model = load_model('custom_training_model_quick.h5')
# encoder_inputs = training_model.input[0]
# encoder_outputs, state_h_enc, state_c_enc = training_model.layers[2].output
# encoder_states = [state_h_enc, state_c_enc]
# encoder_model = Model(encoder_inputs, encoder_states)

# latent_dim = 256
# decoder_state_input_hidden = Input(shape=(latent_dim,))
# decoder_state_input_cell = Input(shape=(latent_dim,))
# decoder_states_inputs = [decoder_state_input_hidden, decoder_state_input_cell]

# decoder_outputs, state_hidden, state_cell = decoder_lstm(decoder_inputs, initial_state=decoder_states_inputs)
# decoder_states = [state_hidden, state_cell]
# decoder_outputs = decoder_dense(decoder_outputs)

# decoder_model = Model([decoder_inputs] + decoder_states_inputs, [decoder_outputs] + decoder_states)

# def decode_response(test_input):
#   #Getting the output states to pass into the decoder
#   states_value = encoder_model.predict(test_input)
#   #Generating empty target sequence of length 1
#   target_seq = np.zeros((1, 1, num_decoder_tokens))
#   #Setting the first token of target sequence with the start token
#   target_seq[0, 0, target_features_dict['<START>']] = 1.
  
#   #A variable to store our response word by word
#   decoded_sentence = ''
  
#   stop_condition = False
#   while not stop_condition:
#     #Predicting output tokens with probabilities and states
#     output_tokens, hidden_state, cell_state = decoder_model.predict([target_seq] + states_value)
#     #Choosing the one with highest probability
#     sampled_token_index = np.argmax(output_tokens[0, -1, :])
#     sampled_token = reverse_target_features_dict[sampled_token_index]
#     decoded_sentence += " " + sampled_token
#     #Stop if hit max length or found the stop token
#     if (sampled_token == '<END>' or len(decoded_sentence) > max_decoder_seq_length):
#       stop_condition = True
#       #Update the target sequence
#     target_seq = np.zeros((1, 1, num_decoder_tokens))
#     target_seq[0, 0, sampled_token_index] = 1.
#     #Update states
#     states_value = [hidden_state, cell_state]
#   return decoded_sentence


# class ChatBot:
#   negative_responses = ("no", "nope", "nah", "naw", "not a chance", "sorry")
#   exit_commands = ("quit", "pause", "exit", "goodbye", "bye", "later", "stop")
# #Method to start the conversation
#   def start_chat(self):
#     user_response = input("Hi, I'm a chatbot trained on random dialogs. Would you like to chat with me?\n")
    
#     if user_response in self.negative_responses:
#       print("Ok, have a great day!")
#       return
#     self.chat(user_response)
# #Method to handle the conversation
#   def chat(self, reply):
#     while not self.make_exit(reply):
#       reply = input(self.generate_response(reply)+"\n")
    
#   #Method to convert user input into a matrix
#   def string_to_matrix(self, user_input):
#     tokens = re.findall(r"[\w']+|[^\s\w]", user_input)
#     user_input_matrix = np.zeros(
#       (1, max_encoder_seq_length, num_encoder_tokens),
#       dtype='float32')
#     for timestep, token in enumerate(tokens):
#       if token in input_features_dict:
#         user_input_matrix[0, timestep, input_features_dict[token]] = 1.
#     return user_input_matrix
  
#   #Method that will create a response using seq2seq model we built
#   def generate_response(self, user_input):
#     input_matrix = self.string_to_matrix(user_input)
#     chatbot_response = decode_response(input_matrix)
#     #Remove <START> and <END> tokens from chatbot_response
#     chatbot_response = chatbot_response.replace("<START>",'')
#     chatbot_response = chatbot_response.replace("<END>",'')
#     return chatbot_response
# #Method to check for exit commands
#   def make_exit(self, reply):
#     for exit_command in self.exit_commands:
#       if exit_command in reply:
#         print("Ok, have a great day!")
#         return True
#     return False

# chatbot = ChatBot()
# chatbot.start_chat()