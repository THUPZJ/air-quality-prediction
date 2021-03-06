# 一个站点，一个指标
# 使用 meo 数据



import tkinter
import os
import pandas as pd
import numpy as np 
import seaborn as sns
import tensorflow as tf
import keras.backend.tensorflow_backend as KTF

from utils.plot_util import plot_forecast_and_actual_example
from metrics.metrics import SMAPE_on_dataset_v1
from seq2seq.seq2seq_data_util import get_training_statistics, generate_training_set, generate_dev_set
from seq2seq.multi_variable_seq2seq_model_parameters import build_graph


os.environ['CUDA_VISIBLE_DEVICES'] = '0'

gpu_config = tf.ConfigProto()
gpu_config.gpu_options.allow_growth = True
session = tf.Session(config=gpu_config)
KTF.set_session(session)


# Args
station_list = ['dongsi_aq','tiantan_aq','guanyuan_aq','wanshouxigong_aq','aotizhongxin_aq',
            'nongzhanguan_aq','wanliu_aq','beibuxinqu_aq','zhiwuyuan_aq','fengtaihuayuan_aq',
            'yungang_aq','gucheng_aq','fangshan_aq','daxing_aq','yizhuang_aq','tongzhou_aq',
            'shunyi_aq','pingchang_aq','mentougou_aq','pinggu_aq','huairou_aq','miyun_aq',
            'yanqin_aq','dingling_aq','badaling_aq','miyunshuiku_aq','donggaocun_aq',
            'yongledian_aq','yufa_aq','liulihe_aq','qianmen_aq','yongdingmennei_aq',
            'xizhimenbei_aq','nansanhuan_aq','dongsihuan_aq']            
X_aq_list = ["PM2.5","PM10","O3","CO","SO2","NO2"]  
y_aq_list = ["PM2.5","PM10","O3"]
X_meo_list = ["temperature","pressure","humidity","direction","speed/kph"]



# 只选一个站点，一个特征预测，同时只使用该站的数据
# 注意要以 list 的形式！！！！
station_list = [station_list[0]]
X_aq_list = X_aq_list
y_aq_list = [y_aq_list[0]]
X_meo_list = X_meo_list


# 调整的参数
use_day=True
learning_rate=1e-3

# 固定的参数
pre_days=5
batch_size=128
input_seq_len = pre_days * 24
output_seq_len = 48
hidden_dim = 32
input_dim = 11
output_dim = 1
num_stacked_layers = 3

lambda_l2_reg=0.003
GRADIENT_CLIPPING=2.5
total_iteractions = 2000
KEEP_RATE = 0.5


# Generate test data for the model
test_x, test_y = generate_dev_set(station_list=station_list,
                                  X_aq_list=X_aq_list, 
                                  y_aq_list=y_aq_list, 
                                  X_meo_list=X_meo_list,
                                  pre_days=pre_days)
print(test_x.shape, test_y.shape)


# # Define training model
# rnn_model = build_graph(feed_previous=False, 
#                         input_seq_len=input_seq_len, 
#                         output_seq_len=output_seq_len, 
#                         hidden_dim=hidden_dim, 
#                         input_dim=input_dim, 
#                         output_dim=output_dim, 
#                         num_stacked_layers=num_stacked_layers, 
#                         learning_rate=learning_rate,
#                         lambda_l2_reg=lambda_l2_reg,
#                         GRADIENT_CLIPPING=GRADIENT_CLIPPING)


# # training process
# train_losses = []
# val_losses = []
# saved_iteractions = []

# saver = tf.train.Saver()
# init = tf.global_variables_initializer()
# with tf.Session() as sess:

#     sess.run(init)
#     losses = []
#     print("Training losses: ")
#     for i in range(total_iteractions):
#         batch_input, batch_output = generate_training_set(station_list=station_list,
#                                                           X_aq_list=X_aq_list,
#                                                           y_aq_list=y_aq_list,
#                                                           X_meo_list=X_meo_list,
#                                                           use_day=use_day,
#                                                           pre_days=pre_days,
#                                                           batch_size=batch_size)

        
#         feed_dict = {rnn_model['enc_inp'][t]: batch_input[:,t,:] for t in range(input_seq_len)}
#         feed_dict.update({rnn_model['target_seq'][t]: batch_output[:,t,:] for t in range(output_seq_len)})
#         _, loss_t = sess.run([rnn_model['train_op'], rnn_model['loss']], feed_dict) 
        
#         if i%10 == 0:
#             print("loss after %d/%d iteractions : %.3f" %(i, total_iteractions, loss_t))

#             temp_saver = rnn_model['saver']()
#             name = 'multivariate_%d_iteractions' %(i)
#             saved_iteractions.append(name)
#             save_path = temp_saver.save(sess, os.path.join('./seq2seq/meo_one_variable_model_results/', name))
#             print("Checkpoint saved at: ", save_path)

#         losses.append(loss_t)



output_features = []
for station in station_list : 
    for aq_feature in y_aq_list :
        output_features.append(station + "_" + aq_feature)

# 特征要和训练时候的特征顺序保持一致
output_features.sort()

# 统计量值
statistics = get_training_statistics()


# predicting using different model
rnn_model = build_graph(feed_previous=True, 
                        input_seq_len=input_seq_len, 
                        output_seq_len=output_seq_len, 
                        hidden_dim=hidden_dim, 
                        input_dim=input_dim, 
                        output_dim=output_dim, 
                        num_stacked_layers=num_stacked_layers, 
                        learning_rate=learning_rate,
                        lambda_l2_reg=lambda_l2_reg,
                        GRADIENT_CLIPPING=GRADIENT_CLIPPING)

aver_smapes_on_iteractions = {}


saved_iteractions = ['multivariate_%d_iteractions' %(i) for i in range(0,total_iteractions,10)]

for name in saved_iteractions :

	init = tf.global_variables_initializer()
	with tf.Session() as sess:

	    sess.run(init)
	    
	    print("Using checkpoint: ", name)
	    saver = rnn_model['saver']().restore(sess,  os.path.join('./seq2seq/meo_one_variable_model_results/', name))
	    
	    feed_dict = {rnn_model['enc_inp'][t]: test_x[:, t, :] for t in range(input_seq_len)} # batch prediction
	    feed_dict.update({rnn_model['target_seq'][t]: np.zeros([test_x.shape[0], output_dim], dtype=np.float32) for t in range(output_seq_len)})
	    final_preds = sess.run(rnn_model['reshaped_outputs'], feed_dict)
	    
	    final_preds = [np.expand_dims(pred, 1) for pred in final_preds]
	    final_preds = np.concatenate(final_preds, axis = 1)

	aver_smapes, smapes_of_features = SMAPE_on_dataset_v1(test_y, final_preds, output_features, statistics, 1)

	aver_smapes_on_iteractions[name] = aver_smapes


print(aver_smapes_on_iteractions)


df_aver_smapes_on_iteractions = pd.Series(aver_smapes_on_iteractions)
df_aver_smapes_on_iteractions.to_csv("data/meo_one_station_one_feature_seq2seq_result.csv")

print("Trianing done! model saved at data/meo_one_station_one_feature_seq2seq_result.csv")














