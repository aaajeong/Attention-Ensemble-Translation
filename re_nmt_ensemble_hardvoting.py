# -*- coding: utf-8 -*-
"""re-nmt_Ensemble_HardVoting

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1_6gQlEsCCBrZp_o2ocHR9obnbbqz-wZV

# **Attention Ensemble  - Hard Voting**
---

### **구글 드라이브 Mount**
"""

# from google.colab import drive
# drive.mount('/content/drive')

"""### **Import Libraries**"""

import tensorflow as tf
from keras.models import Model
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from sklearn.model_selection import train_test_split 

import unicodedata
import re
import numpy as np
import os
import io
import time
import random

"""### **데이터 로드**"""

path_to_file = '/content/drive/MyDrive/Colab Notebooks/spa-eng/spa.txt'
path_to_file_esb = '/content/drive/MyDrive/Colab Notebooks/spa-eng/spa_for_esb.txt'

"""### **데이터 랜덤 셔플**


*   [영어, 스페인어] 쌍 shuffle file 새로 저장
*   번역 테스트 시 주석 처리


"""

# lines = io.open(path_to_file, encoding='UTF-8').read().strip().split('\n')
# random.shuffle(lines)
# f = open(path_to_file_esb, 'w')
# for i in lines:
#     data = i + '\n'
#     f.write(data)
# f.close()

"""### **데이터(문장) 전처리**"""

# 유니코드 파일을 아스키 코드 파일로 변환합니다.
def unicode_to_ascii(s):
  return ''.join(c for c in unicodedata.normalize('NFD', s)
      if unicodedata.category(c) != 'Mn')


def preprocess_sentence(w):
  w = unicode_to_ascii(w.lower().strip())

  # 단어와 단어 뒤에 오는 구두점(.)사이에 공백을 생성합니다.
  # 예시: "he is a boy." => "he is a boy ."
  # 참고:- https://stackoverflow.com/questions/3645931/python-padding-punctuation-with-white-spaces-keeping-punctuation
  w = re.sub(r"([?.!,¿])", r" \1 ", w)
  w = re.sub(r'[" "]+', " ", w)

  # (a-z, A-Z, ".", "?", "!", ",")을 제외한 모든 것을 공백으로 대체합니다.
  w = re.sub(r"[^a-zA-Z?.!,¿]+", " ", w)

  w = w.strip()

  # 모델이 예측을 시작하거나 중단할 때를 알게 하기 위해서
  # 문장에 start와 end 토큰을 추가합니다.
  w = '<start> ' + w + ' <end>'
  return w

"""### **Dataset 생성**
1. 문장에 있는 억양을 제거합니다.
2. 불필요한 문자를 제거하여 문장을 정리합니다.
3. 다음과 같은 형식으로 문장의 쌍을 반환합니다: [영어, 스페인어]
"""

def create_dataset(path, num_examples):
  lines = io.open(path, encoding='UTF-8').read().strip().split('\n')

  word_pairs = [[preprocess_sentence(w) for w in l.split('\t')]  for l in lines[:num_examples]]

  return zip(*word_pairs)

"""### **Language 가 들어오면 공백 단위로 토큰화**
- fit_on_texts(): 문자 데이터를 입력받아서 리스트의 형태로 변환
- texts_to_sequences: 텍스트 안의 단어들을 숫자 시퀀스로 출력
- pad_sequcences(tensor, padding='post') : 서로 다른 개수의 단어로 이루어진 문장을 같은 길이로 만들어주기 위해 패딩을 사용
  - padding = 'post' : [[ 0  0  0  5  3  2  4], [ 0  0  0  5  3  2  7],...,]
  - padding = 'pre' : 뒤 부터 패딩이 채워짐
  - 가장 긴 sequence 의 길이 만큼
  
"""

def tokenize(lang):
  lang_tokenizer = tf.keras.preprocessing.text.Tokenizer(
      filters='')
  lang_tokenizer.fit_on_texts(lang)

  tensor = lang_tokenizer.texts_to_sequences(lang)

  tensor = tf.keras.preprocessing.sequence.pad_sequences(tensor,
                                                         padding='post')

  return tensor, lang_tokenizer

"""### **전처리된 타겟 문장과 입력 문장 쌍을 생성**
- input_tensor : input 문장의 패딩 처리된 숫자 시퀀스
- inp_lang_tokenizer : input 문장을 공백 단위로 토큰화, 문자 -> 리스트 변환
- target_tensor, targ_lang_tokenizer : 위와 비슷

"""

def load_dataset(path, num_examples=None):
  
  targ_lang, inp_lang = create_dataset(path, num_examples)

  input_tensor, inp_lang_tokenizer = tokenize(inp_lang)
  target_tensor, targ_lang_tokenizer = tokenize(targ_lang)

  return input_tensor, target_tensor, inp_lang_tokenizer, targ_lang_tokenizer

"""### **언어 데이터셋 크기 제한**
- 언어 데이터셋을 아래의 크기로 제한하여 훈련과 검증을 수행
- inp_lang, targ_lang : 인풋,타겟 문장의 문자 -> 리스트 변환 결과
- max_length_targ, max_length_inp : 인풋, 타겟 문장의 '패딩된' 숫자 시퀀스 길이 -> 타겟 텐서와 입력 텐서의 최대 길이
"""

num_examples = 30000
input_tensor, target_tensor, inp_lang, targ_lang = load_dataset(path_to_file_esb, num_examples)
# input_tensor2, target_tensor2, inp_lang2, targ_lang2 = load_dataset(path_to_file, 1, num_examples)
# input_tensor3, target_tensor3, inp_lang3, targ_lang3 = load_dataset(path_to_file, 2, num_examples)


max_length_targ, max_length_inp = target_tensor.shape[1], input_tensor.shape[1]
# max_length_targ2, max_length_inp2 = target_tensor2.shape[1], input_tensor2.shape[1]
# max_length_targ3, max_length_inp3 = target_tensor3.shape[1], input_tensor3.shape[1]

"""### **데이터셋 (테스트 & 검증) 분리**"""

# 훈련 집합과 검증 집합을 80대 20으로 분리합니다.
input_tensor_train, input_tensor_val, target_tensor_train, target_tensor_val = train_test_split(input_tensor, target_tensor, test_size=0.2)

# 훈련 집합과 검증 집합의 데이터 크기를 출력합니다.
print(len(input_tensor_train), len(target_tensor_train), len(input_tensor_val), len(target_tensor_val))

"""### 인덱스 -> 해당 word 로

```
Input Language; index to word mapping
1 ----> <start>
93 ----> tomas
27 ----> le
1063 ----> escribio
7 ----> a
120 ----> maria
3 ----> .
2 ----> <end>
```


```
Target Language; index to word mapping
1 ----> <start>
8 ----> tom
695 ----> wrote
6 ----> to
31 ----> mary
3 ----> .
2 ----> <end>
```


"""

def convert(lang, tensor):
  for t in tensor:
    if t!=0:
      print ("%d ----> %s" % (t, lang.index_word[t]))

"""### **Buffer, Batch, epoch, embedding dimension, units 설정**
- Tokenizer 의 word_index 속성 : 속성은 단어와 숫자의 키-값 쌍을 포함하는 딕셔너리를 반환
- 따라서 vocab_inp_size, vocab_inp_size : 인풋, 타겟의 단어-숫자 딕셔너리 최대 길이 + 1 (?)
- dataset.batch(BATCH_SIZE, drop_remainder = True) : 배치사이즈 만큼 분할 후 남은 데이터를 drop 할 것인지 여부
- shuffle : 데이터셋 적절히 섞어준다.
"""

BUFFER_SIZE = len(input_tensor_train)
BATCH_SIZE = 64
steps_per_epoch = len(input_tensor_train)//BATCH_SIZE
embedding_dim = 256
units = 1024
vocab_inp_size = len(inp_lang.word_index)+1
vocab_tar_size = len(targ_lang.word_index)+1

# 훈련 집합에서만 shuffle, batch
dataset = tf.data.Dataset.from_tensor_slices((input_tensor_train, target_tensor_train)).shuffle(BUFFER_SIZE)
dataset = dataset.batch(BATCH_SIZE, drop_remainder=True)

example_input_batch, example_target_batch = next(iter(dataset))
example_input_batch.shape, example_target_batch.shape

"""### **Encoder**


1.   초기화 : vocab_size(단어의 크기), embedding_dim(임베딩 차원 수), enc_units(인코더의 히든 사이즈), batch_sz(배치 사이즈)
  - embedding_dim : 단어 -> 임베딩 벡터로 하기 위한 차원 수
2.  call : gru 에 들어가 output, state 출력
3.  initialize_hidden_state : 맨 처음 gru에 들어가기 위한 더미 입력 값



"""

class Encoder(tf.keras.Model):
  def __init__(self, vocab_size, embedding_dim, enc_units, batch_sz):
    super(Encoder, self).__init__()
    self.batch_sz = batch_sz
    self.enc_units = enc_units
    self.embedding = tf.keras.layers.Embedding(vocab_size, embedding_dim)
    self.gru = tf.keras.layers.GRU(self.enc_units,
                                   return_sequences=True,
                                   return_state=True,
                                   recurrent_initializer='glorot_uniform')

  def call(self, x, hidden):
    x = self.embedding(x)
    output, state = self.gru(x, initial_state = hidden)
    return output, state

  def initialize_hidden_state(self):
    return tf.zeros((self.batch_sz, self.enc_units))

"""### **Encoder 객체 생성**"""

# encoder = Encoder(vocab_inp_size, embedding_dim, units, BATCH_SIZE)

"""### **Attention**

"""

class BahdanauAttention(tf.keras.layers.Layer):
  def __init__(self, units):
    super(BahdanauAttention, self).__init__()
    self.W1 = tf.keras.layers.Dense(units)
    self.W2 = tf.keras.layers.Dense(units)
    self.V = tf.keras.layers.Dense(1)

  def call(self, query, values):
    # 쿼리 은닉 상태(query hidden state)는 (batch_size, hidden size)쌍으로 이루어져 있습니다.
    # query_with_time_axis은 (batch_size, 1, hidden size)쌍으로 이루어져 있습니다.
    # values는 (batch_size, max_len, hidden size)쌍으로 이루어져 있습니다.
    # 스코어(score)계산을 위해 덧셈을 수행하고자 시간 축을 확장하여 아래의 과정을 수행합니다.
    query_with_time_axis = tf.expand_dims(query, 1)

    # score는 (batch_size, max_length, 1)쌍으로 이루어져 있습니다.
    # score를 self.V에 적용하기 때문에 마지막 축에 1을 얻습니다.
    # self.V에 적용하기 전에 텐서는 (batch_size, max_length, units)쌍으로 이루어져 있습니다.
    score = self.V(tf.nn.tanh(
        self.W1(query_with_time_axis) + self.W2(values)))

    # attention_weights는 (batch_size, max_length, 1)쌍으로 이루어져 있습니다. 
    attention_weights = tf.nn.softmax(score, axis=1)

    # 덧셈이후 컨텍스트 벡터(context_vector)는 (batch_size, hidden_size)쌍으로 이루어져 있습니다.
    context_vector = attention_weights * values
    context_vector = tf.reduce_sum(context_vector, axis=1)

    return context_vector, attention_weights

"""### **Decoder**


1.   초기화 : vocab_size(단어의 크기), embedding_dim(임베딩 차원 수), enc_units(인코더의 히든 사이즈), batch_sz(배치 사이즈)
2.   encoder 와의 차이점 : 마지막 fully_connected_layer(tf.keras.layers.Dense) 추가


"""

class Decoder(tf.keras.Model):
  def __init__(self, vocab_size, embedding_dim, dec_units, batch_sz):
    super(Decoder, self).__init__()
    self.batch_sz = batch_sz
    self.dec_units = dec_units
    self.embedding = tf.keras.layers.Embedding(vocab_size, embedding_dim)
    self.gru = tf.keras.layers.GRU(self.dec_units,
                                   return_sequences=True,
                                   return_state=True,
                                   recurrent_initializer='glorot_uniform')
    self.fc = tf.keras.layers.Dense(vocab_size)

    # 어텐션을 사용합니다.
    self.attention = BahdanauAttention(self.dec_units)

  def call(self, x, hidden, enc_output):
    # enc_output는 (batch_size, max_length, hidden_size)쌍으로 이루어져 있습니다.
    context_vector, attention_weights = self.attention(hidden, enc_output)

    # 임베딩층을 통과한 후 x는 (batch_size, 1, embedding_dim)쌍으로 이루어져 있습니다.
    x = self.embedding(x)

    # 컨텍스트 벡터와 임베딩 결과를 결합한 이후 x의 형태는 (batch_size, 1, embedding_dim + hidden_size)쌍으로 이루어져 있습니다.
    x = tf.concat([tf.expand_dims(context_vector, 1), x], axis=-1)

    # 위에서 결합된 벡터를 GRU에 전달합니다.
    output, state = self.gru(x)

    # output은 (batch_size * 1, hidden_size)쌍으로 이루어져 있습니다.
    output = tf.reshape(output, (-1, output.shape[2]))

    # output은 (batch_size, vocab)쌍으로 이루어져 있습니다.
    x = self.fc(output)

    # return x, state, attention_weights
    return x, state

"""### **Decoder 객체 생성**"""

# decoder = Decoder(vocab_tar_size, embedding_dim, units, BATCH_SIZE)

"""### **NMT Model 생성**"""

class NMT_Model():
  def __init__(self):
    super(NMT_Model, self).__init__()
    self.encoder = Encoder(vocab_inp_size, embedding_dim, units, BATCH_SIZE)
    self.decoder = Decoder(vocab_tar_size, embedding_dim, units, BATCH_SIZE)

"""### **Ensemble Model 생성**"""

models = []
num_models = 2
for m in range(num_models):
  m = NMT_Model()
  models.append(m)

# # 각 모델 호출하려면 
# for model in models:
#   print(model)
# for m in range(num_models):
#     models.append(NMT_Model())
# print(models)

# for model in models:
#   sample_hidden = model.encoder.initialize_hidden_state()
#   sample_output, sample_hidden = model.encoder(example_input_batch, sample_hidden)
#   print ('Encoder output shape: (batch size, sequence length, units) {}'.format(sample_output.shape))
#   print ('Encoder Hidden state shape: (batch size, units) {}'.format(sample_hidden.shape))

# for model in models:
#   sample_decoder_output, _ = model.decoder(tf.random.uniform((BATCH_SIZE, 1)),
#                                         sample_hidden, sample_output)
#   print ('Decoder output shape: (batch_size, vocab size) {}'.format(sample_decoder_output.shape))

"""### **Loss Function & Optimizer**"""

optimizer = tf.keras.optimizers.Adam()
loss_object = tf.keras.losses.SparseCategoricalCrossentropy(
    from_logits=True, reduction='none')

def loss_function(real, pred):
  mask = tf.math.logical_not(tf.math.equal(real, 0))
  loss_ = loss_object(real, pred)

  mask = tf.cast(mask, dtype=loss_.dtype)
  loss_ *= mask

  return tf.reduce_mean(loss_)

"""### **Chekcpoint**
- 여기서 학습한 매개변수를 저장, optimizer/encoder/decoder
"""

checkpoint_dir = '/content/drive/MyDrive/Colab Notebooks/training_checkpoints_esb'
checkpoint_prefix = os.path.join(checkpoint_dir, "ckpt")
checkpoints = []

for m in range(num_models):
  checkpoint = tf.train.Checkpoint(optimizer=optimizer,
                                 encoder=models[m].encoder,
                                 decoder=models[m].decoder)
  checkpoints.append(checkpoint)

print(checkpoints)

"""### **Train_step**"""

# @tf.function
def train_step(model, inp, targ, enc_hidden):
  loss = 0

  with tf.GradientTape() as tape:
    enc_output, enc_hidden = model.encoder(inp, enc_hidden)

    dec_hidden = enc_hidden

    dec_input = tf.expand_dims([targ_lang.word_index['<start>']] * BATCH_SIZE, 1)

    # 교사 강요(teacher forcing) - 다음 입력으로 타겟을 피딩(feeding)합니다.
    for t in range(1, targ.shape[1]):
      # enc_output를 디코더에 전달합니다.
      predictions, dec_hidden = model.decoder(dec_input, dec_hidden, enc_output)
      # print('predictions', predictions.shape)

      loss += loss_function(targ[:, t], predictions)

      # 교사 강요(teacher forcing)를 사용합니다. -> 훈련에서는 실제 값을 이용
      dec_input = tf.expand_dims(targ[:, t], 1)

  batch_loss = (loss / int(targ.shape[1]))
  variables = model.encoder.trainable_variables + model.decoder.trainable_variables
  gradients = tape.gradient(loss, variables)
  optimizer.apply_gradients(zip(gradients, variables))
  return batch_loss

"""### **학습**"""

EPOCHS = 10
model_loss = {0 : 0, 1 : 0, 2 : 0}

for epoch in range(EPOCHS):
  start = time.time()

  total_loss_0 = 0
  total_loss_1 = 0
  enc_hidden = models[0].encoder.initialize_hidden_state()
  # m1_train_step = train_step()
  # m2_train_step = train_step()
  for (batch, (inp, targ)) in enumerate(dataset.take(steps_per_epoch)):

      batch_loss_0 = train_step(models[0], inp, targ, enc_hidden)
      batch_loss_1 = train_step(models[1], inp, targ, enc_hidden)
      # batch_loss_2 = train_step(models[0], inp, targ, enc_hidden)

      total_loss_0 += batch_loss_0
      total_loss_1 += batch_loss_1

      if batch % 100 == 0:
        print('Model {} Epoch {} Batch {} Loss {:.4f}'.format(models[0], epoch + 1,
                                                    batch,
                                                    batch_loss_0.numpy()))
        print('Model {} Epoch {} Batch {} Loss {:.4f}'.format(models[1], epoch + 1,
                                                    batch,
                                                    batch_loss_1.numpy()))
  # 각 모델의 최종 loss 를 저장
  model_loss[0] = total_loss_0
  model_loss[1] = total_loss_1

  # 에포크가 2번 실행될때마다 모델 저장 (모델 별 체크포인트)
  if (epoch + 1) % 2 == 0:
    for idx, checkpoint in enumerate(checkpoints):
      checkpoint.save(file_prefix=checkpoint_prefix+'-{}'.format(idx))

  print('Model 1 : Epoch {} Loss {:.4f}'.format(epoch + 1,
                                      model_loss[0] / steps_per_epoch))
  print('Model 2 : Epoch {} Loss {:.4f}'.format(epoch + 1,
                                      model_loss[1] / steps_per_epoch))
  # print('Model 3 : Epoch {} Loss {:.4f}'.format(epoch + 1,
  #                                     model_loss[2] / steps_per_epoch))
  print('Time taken for 1 epoch {} sec\n'.format(time.time() - start))

# EPOCHS = 1
# model_loss = {0 : 0, 1 : 0, 2 : 0}

# for epoch in range(EPOCHS):
#   start = time.time()
  
#   for i, model in enumerate(models):
#     # print('model', model)
#     # train_encoder = model.encoder
#     # train_decoder = model.decoder
#     # print(train_encoder)
#     # print(train_decoder)
#     total_loss = 0
#     enc_hidden = model.encoder.initialize_hidden_state()

#     for (batch, (inp, targ)) in enumerate(dataset.take(steps_per_epoch)):

#       batch_loss = train_step(model, inp, targ, enc_hidden)

#       total_loss += batch_loss

#       if batch % 100 == 0:
#         print('Model {} Epoch {} Batch {} Loss {:.4f}'.format(model, epoch + 1,
#                                                     batch,
#                                                     batch_loss.numpy()))
#     # 각 모델의 최종 loss 를 저장
#     model_loss[i] = total_loss  
  
#     # 에포크가 2번 실행될때마다 모델 저장 (모델 별 체크포인트)
#   if (epoch + 1) % 2 == 0:
#     for idx, checkpoint in enumerate(checkpoints):
#       checkpoint.save(file_prefix=checkpoint_prefix+'-{}'.format(idx))

#   print('Model 1 : Epoch {} Loss {:.4f}'.format(epoch + 1,
#                                       model_loss[0] / steps_per_epoch))
#   print('Model 2 : Epoch {} Loss {:.4f}'.format(epoch + 1,
#                                       model_loss[1] / steps_per_epoch))
#   # print('Model 3 : Epoch {} Loss {:.4f}'.format(epoch + 1,
#   #                                     model_loss[2] / steps_per_epoch))
#   print('Time taken for 1 epoch {} sec\n'.format(time.time() - start))

"""### **문장 번역(스페인 -> 영어)** 

*   tf.keras.preprocessing.sequence.pad_sequences([inputs], maxlen='', padding='post') : 일정한 길이(maxlen)로 맞춰준다. (패딩은 뒤에서)
*   

  ```
  inp_lang.word_index :  {'<start>': 1, '<end>': 2, '.': 3, 'tom': 4, '?': 5...}
  ```

* tf.expand_dims: 차원을 늘려준다.



"""

def evaluate(sentence):
  # 어텐션 그래프
  # attention_plot = np.zeros((max_length_targ, max_length_inp))

  # print('model1 : ', models[0])
  # print('model2 : ', models[1])
  # print('model3 : ', models[2])


  sentence = preprocess_sentence(sentence)

  # 문장, input 딕셔너리 출력 
  print ('sentence:', sentence)

  inputs = [inp_lang.word_index[i] for i in sentence.split(' ')]
  inputs = tf.keras.preprocessing.sequence.pad_sequences([inputs],
                                                         maxlen=max_length_inp,
                                                         padding='post')
  inputs2 = [inp_lang.word_index[i] for i in sentence.split(' ')]
  inputs2 = tf.keras.preprocessing.sequence.pad_sequences([inputs2],
                                                         maxlen=max_length_inp,
                                                         padding='post')
  # inputs3 = [inp_lang.word_index[i] for i in sentence.split(' ')]
  # inputs3 = tf.keras.preprocessing.sequence.pad_sequences([inputs3],
  #                                                        maxlen=max_length_inp,
  #                                                        padding='post')
  inputs = tf.convert_to_tensor(inputs)
  inputs2 = tf.convert_to_tensor(inputs2)
  # inputs3 = tf.convert_to_tensor(inputs3)


  result1 = ''
  result2 = ''
  final_result1 = ''
  final_result2 = ''
  # result3 = ''

  hidden = [tf.zeros((1, units))]
  hidden2 = [tf.zeros((1, units))]
  # hidden3 = [tf.zeros((1, units))]

  # Encoder 의 hidden 을 Decoder 의 hidden 으로 받는다.
  enc_out, enc_hidden = models[0].encoder(inputs, hidden)
  print('enc_out', enc_out.shape)
  enc_out2, enc_hidden2 = models[1].encoder(inputs2, hidden2)
  print('enc_out2', enc_out2.shape)
  # enc_out3, enc_hidden3 = models[2].encoder(inputs3, hidden3)
  # print('enc_out3', enc_out3.shape)


  dec_hidden = enc_hidden
  dec_hidden2 = enc_hidden2
  # dec_hidden3 = enc_hidden3


  # Decoder 의 시작인 '<start>' 
  dec_input = tf.expand_dims([targ_lang.word_index['<start>']], 0)
  dec_input2 = tf.expand_dims([targ_lang.word_index['<start>']], 0)
  # dec_input3 = tf.expand_dims([targ_lang.word_index['<start>']], 0)

  # Target 의 최대 길이 만큼 출력
  for t in range(max_length_inp):
    predictions, dec_hidden = models[0].decoder(dec_input,
                                                         dec_hidden,
                                                         enc_out)
    predictions2, dec_hidden2 = models[1].decoder(dec_input2,
                                                         dec_hidden2,
                                                         enc_out2)
    # predictions3, dec_hidden3 = models[2].decoder(dec_input3,
    #                                                      dec_hidden3,
    #                                                      enc_out3)
    
    predicted_id = tf.argmax(predictions[0]).numpy() 
    predicted_id2 = tf.argmax(predictions2[0]).numpy() 
    # predicted_id3 = tf.argmax(predictions3[0]).numpy() 

    # voting = {}
    # if predicted_id not in voting:
    #   voting[predicted_id] = 1
    # else :
    #   voting[predicted_id] += 1
    
    # if predicted_id2 not in voting:
    #   voting[predicted_id2] = 1
    # else :
    #   voting[predicted_id2] += 1
    
    # if predicted_id3 not in voting:
    #   voting[predicted_id3] = 1
    # else :
    #   voting[predicted_id3] += 1
    # print(voting)
    # # print(max(voting,key=voting.get)) # di.get 이용

    # voting_id = max(voting,key=voting.get)


    # result += targ_lang.index_word[voting_id] + ' '
    # print('result: ', result)

    # if targ_lang.index_word[voting_id] == '<end>':
    #   # return result, sentence, attention_plot
    #   return result, sentence

    # # 예측된 ID를 모델에 다시 피드합니다.
    # dec_input = tf.expand_dims([voting_id], 0)
    # print("for 문 후 dec_input : ", dec_input)

  # for t in range(max_length_targ):
  #   predictions, dec_hidden, attention_weights = decoder(dec_input,
  #                                                        dec_hidden,
  #                                                        enc_out)

    # 나중에 어텐션 가중치를 시각화하기 위해 어텐션 가중치를 저장합니다.
    # attention_weights = tf.reshape(attention_weights, (-1, ))
    # attention_plot[t] = attention_weights.numpy()

#     predicted_id_list = []   # 제일 큰 확률 5개의 id 저장 리스트 (확률 값이 아니라 해당 아이디!!!!)
#     search_max_predictions = list(predictions[0])  # 큰 값 5개를 찾기 위해서 임시로 복사한 확률 분포 리스트
#     for i in range(5):
#         argmax_id = tf.argmax(search_max_predictions).numpy() # 확률 제일 큰 값 
#         predicted_id_list.append(argmax_id)
#         del search_max_predictions[argmax_id]  # 찾은 제일 큰 값 리스트에서 삭제 -> 다음 루프에서 그 다음으로 큰 값 찾기
    
#     # 예측된 5개의 id 에 해당하는 단어 출력
#     for i in predicted_id_list:
#         print(i, ' : ', targ_lang.index_word[i])
        
#     # 다음 나올 단어 입력
#     predicted_id = int(input("다음 단어의 ID 를 입력하세요 : "))
# #     predicted_id = max(predicted_id_list)
    
#     print('predicted_id_list : ', predicted_id_list)
    

    result1 += targ_lang.index_word[predicted_id] + ' '
    result2 += targ_lang.index_word[predicted_id2] + ' '
    # result3 += targ_lang.index_word[predicted_id3] + ' '

    # if targ_lang.index_word[predicted_id] == '<end>':
    #   final_result1 = result1
    #   # return result1, result2, sentence
    # if targ_lang.index_word[predicted_id2] == '<end>':
    #   final_result2 = result2
    if (targ_lang.index_word[predicted_id2] == '<end>') or (targ_lang.index_word[predicted_id] == '<end>'):
      return result1, result2, sentence

    # 예측된 ID를 모델에 다시 피드합니다.
    dec_input = tf.expand_dims([predicted_id], 0)
    dec_input2 = tf.expand_dims([predicted_id2], 0)
    # dec_input3 = tf.expand_dims([predicted_id3], 0)

  # return result, sentence, attention_plot
  return result1, result2, sentence

def translate(sentence):
  # result, sentence = evaluate(sentence)
  # result1, result2, result3, sentence = evaluate(sentence)
  result1, result2, sentence = evaluate(sentence)
  
  print('Input: %s' % (sentence))
  print('Model 1 의 Predicted translation: {}'.format(result1))
  print('Model 2 의 Predicted translation: {}'.format(result2))
  # print('Model 3 의 Predicted translation: {}'.format(result3))

  # attention_plot = attention_plot[:len(result.split(' ')), :len(sentence.split(' '))]
#   plot_attention(attention_plot, sentence.split(' '), result.split(' '))

"""### **Checkpoint 복원**"""

# checkpoint_dir내에 있는 최근 체크포인트(checkpoint)를 복원
checkpoint.restore(tf.train.latest_checkpoint(checkpoint_dir))
# for idx, checkpoint in enumerate(checkpoints):
#       checkpoint.restore(tf.train.latest_checkpoint(checkpoint_dir))

# for m in range(num_models):
#   checkpoint = tf.train.Checkpoint(optimizer=optimizer,
#                                  encoder=models[m].encoder,
#                                  decoder=models[m].decoder)
#   checkpoint.restore(tf.train.latest_checkpoint(checkpoint_dir))

# for idx, checkpoint in enumerate(checkpoints):
#       checkpoint.restore(file_prefix=checkpoint_prefix+'-{}'.format(idx))

"""### **번역 시작**"""

translate(u'hace mucho frio aqui.')  # it s very cold here

translate(u'esta es mi vida.')  # this is my life

translate(u'¿todavia estan en casa?')  # Are you still at home?

# 잘못된 번역
# translate(u'trata de averiguarlo.')   # try to find out / try to figure out

# translate(u'Te quiero')   # I love you