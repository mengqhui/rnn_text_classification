#-*- coding:utf-8 -*-

import tensorflow as tf
import numpy as np

class BiRNN(object):
	"""
	用于文本分类的双向RNN
	"""
	def __init__(self, rnn_size, layer_size, vocab_size, batch_size, sequence_length, n_classes, grad_clip):

		self.output_keep_prob = tf.placeholder(tf.float32, name='output_keep_prob')
		self.input_data = tf.placeholder(tf.int32, shape=[None, sequence_length], name='input_data')
		self.targets = tf.placeholder(tf.float32, shape=[None, n_classes], name='targets')

		# 定义前向RNN Cell
		with tf.name_scope('fw_rnn'), tf.variable_scope('fw_rnn'):
			print tf.get_variable_scope().name
			lstm_fw_cell_list = [tf.contrib.rnn.LSTMCell(rnn_size) for _ in xrange(layer_size)]
			lstm_fw_cell_m = tf.contrib.rnn.DropoutWrapper(tf.contrib.rnn.MultiRNNCell(lstm_fw_cell_list), output_keep_prob=self.output_keep_prob)

		# 定义反向RNN Cell
		with tf.name_scope('bw_rnn'), tf.variable_scope('bw_rnn'):
			print tf.get_variable_scope().name
			lstm_bw_cell_list = [tf.contrib.rnn.LSTMCell(rnn_size) for _ in xrange(layer_size)]
			lstm_bw_cell_m = tf.contrib.rnn.DropoutWrapper(tf.contrib.rnn.MultiRNNCell(lstm_fw_cell_list), output_keep_prob=self.output_keep_prob)


		with tf.device('/cpu:0'):
			embedding = tf.Variable(tf.truncated_normal([vocab_size, rnn_size], stddev=0.1), name='embedding')
			inputs = tf.nn.embedding_lookup(embedding, self.input_data)

		# self.input_data shape: (batch_size , sequence_length)
		# inputs shape : (batch_size , sequence_length , rnn_size)

		# bidirection rnn 的inputs shape 要求是(sequence_length, batch_size, rnn_size)
		# 因此这里需要对inputs做一些变换
		# 经过transpose的转换已经将shape变为(sequence_length, batch_size, rnn_size)
		# 只是双向rnn接受的输入必须是一个list,因此还需要后续两个步骤的变换
		inputs = tf.transpose(inputs, [1,0,2])
		# 转换成(batch_size * sequence_length, rnn_size)
		inputs = tf.reshape(inputs, [-1, rnn_size])
		# 转换成list,里面的每个元素是(batch_size, rnn_size)
		inputs = tf.split(inputs, sequence_length, 0)

		with tf.name_scope('bw_rnn'), tf.variable_scope('bw_rnn'):
			outputs, _, _ = tf.contrib.rnn.static_bidirectional_rnn(lstm_fw_cell_m, lstm_bw_cell_m, inputs, dtype=tf.float32)

		# outputs shape: (sequence_length, batch_size, 2*rnn_size)
		softmax_w = tf.Variable(tf.truncated_normal([2*rnn_size, n_classes], stddev=0.1), name='softmax_w')
		softmax_b = tf.Variable(tf.zeros([n_classes]), name='softmax_b')

		# 用于分类任务, outputs取最终一个时刻的输出
		self.logits = tf.matmul(outputs[-1], softmax_w) + softmax_b
		self.prob = tf.nn.softmax(self.logits)

		self.cost = tf.losses.softmax_cross_entropy(self.targets, self.logits)
		self.lr = tf.Variable(0.0, trainable=False)
		tvars = tf.trainable_variables()
		grads, _ = tf.clip_by_global_norm(tf.gradients(self.cost, tvars), grad_clip)

		optimizer = tf.train.AdamOptimizer(self.lr)
		self.train_op = optimizer.apply_gradients(zip(grads, tvars))
		self.accuracy = tf.reduce_mean(tf.cast(tf.equal(tf.argmax(self.targets, axis=1), tf.argmax(self.prob, axis=1)), tf.float32))

	def inference(self, sess, labels, inputs):

		prob = sess.run(self.prob, feed_dict={self.input_data:inputs, self.output_keep_prob:1.0})
		ret = np.argmax(prob, 1)
		ret = [labels[i] for i in ret]
		return ret


if __name__ == '__main__':
	model = BiRNN(128, 2, 100, 50, 30, 3000, 5)