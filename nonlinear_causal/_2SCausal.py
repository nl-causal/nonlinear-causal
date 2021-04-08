import numpy as np
from sklearn.base import BaseEstimator
from sklearn.preprocessing import normalize
from sliced import SlicedInverseRegression
from sklearn.neighbors import KNeighborsRegressor
from nonlinear_causal.CDLoop import elastCD
from scipy.stats import norm

class _2SLS(object):
	"""Two-stage least square

	Parameters
	----------

	"""
	def __init__(self, theta=None, beta=None, normalize=True, sparse_reg=elasticSUM()):
		self.theta = theta
		self.beta = beta
		self.normalize = normalize
		self.sparse_reg = sparse_reg
		self.X_LS = None
		self.fit_flag = False

	def fit(self, LD_Z, cor_ZX, cor_ZY):
		self.theta = np.dot(np.linalg.inv( LD_Z ), cor_ZX)
		if self.sparse_reg == None:
			if self.normalize == True:
				self.theta = normalize(self.theta.reshape(1, -1))[0]
			LD_X = self.theta.T.dot(LD_Z).dot(self.theta)
			if LD_X.ndim == 0:
				self.beta = self.theta.T.dot(cor_ZY) / LD_X
			else:
				self.beta = np.linalg.inv(LD_X).dot(self.theta.T).dot(cor_ZY)
		elif self.sparse_reg.fit_flag:
			self.beta = self.sparse_reg.beta[-1]
		else:
			self.X_LS = np.dot(Z, self.theta)
			Z_aug = np.hstack((Z, self.X_LS))
			cov_aug = np.hstack((cor_ZY, np.dot(self.theta, cor_ZY)))
			LD_Z_aug = np.dot(Z_aug.T, Z_aug)
			self.sparse_reg.fit(LD_Z_aug, cov_aug)
			self.beta = self.sparse_reg.beta[-1]
		self.fit_flag = True
	
	def CI_beta(Z, alpha):
		if self.fit_flag:
			cov_Z = np.cov(Z,rowvar=False)
			var_beta = 1. / (self.theta.dot(cov_Z) * self.theta).sum(axis=1)[0]
			delta_tmp = abs(norm.ppf((1. - alpha)/2)) * np.sqrt(var_beta) / np.sqrt(len(Z))
			beta_low = self.beta -  delta_tmp
			beta_high = self.beta + delta_tmp
			return [beta_low, beta_high]
		else:
			raise NameError('CI can only be generated after fit!')



class elasticSUM(object):
	"""Elastic Net based on summary statistics

	Parameters
	----------
	"""

	def __init__(self, lam=1., max_iter=1000, eps=1e-4, print_step=0, criterion='bic'):
		self.lam1 = lam
		self.lam2 = 0.
		self.beta = []
		self.max_iter = max_iter
		self.eps = eps
		self.print_step = print_step
		self.criterion = criterion
		self.fit_flag = False
	
	def fit(self, LD_X, cov):
		"""
		fit the linear coeff based on feature and summary statistics.

		Parameters
		----------
		"""
		if (type(lam1) == int or float):
			self.beta = elastCD(LD_X, cov, self.lam1, self.lam2, self.max_iter, self.eps, self.print_step)
			self.fit_flag = True
		else:
			lam_lst, beta_path, df_lst = [], [], []
			for lam_tmp in self.lam1:
				beta_tmp = elastCD(LD_X, cov, lam_tmp, self.lam2, self.max_iter, self.eps, self.print_step)
				df_tmp = np.sum(np.abs(beta_tmp) > self.eps)
				df_lst.append(df_tmp)
				beta_path.append(beta_tmp)
				lam_lst.append(lam_tmp)
			lam_lst, beta_path, df_lst = np.array(lam_lst), np.array(beta_path), np.array(df_lst)
			## compute criteria


	def predict(self, X):
		return np.dot(X, self.beta)

class _2SIR(object):
	"""Sliced inverse regression + least sqaure

	Parameters
	----------

	"""
	def __init__(self, theta=None, beta=None, sir=None, n_directions=1, n_slices='auto', data_in_slice=50, cond_mean=KNeighborsRegressor(n_neighbors=10), fit_link=True, sparse_reg=elasticSUM()):
		self.theta = theta
		self.beta = beta
		self.n_directions = n_directions
		self.n_slices = n_slices
		self.data_in_slice = data_in_slice
		self.fit_link = fit_link
		self.cond_mean = cond_mean
		self.sir = None
		self.X_sir = None
		self.rho = None
		self.sparse_reg = sparse_reg

	def fit_sir(self, Z, X):
		if self.n_slices == 'auto':
			n_slices = int(len(Z) / self.data_in_slice)
		else:
			n_slices = self.n_slices
		self.sir = SlicedInverseRegression(n_directions=self.n_directions, n_slices=n_slices)
		self.sir.fit(Z, X)
		self.X_sir = self.sir.transform(Z)
		self.theta = self.sir.directions_

	def fit_reg(self, Z, cor_ZY):
		if self.sparse_reg == None:
			LD_X_sir = np.dot(self.X_sir.T, self.X_sir)
			if LD_X_sir.ndim == 0:
				self.beta = np.dot(self.theta, cor_ZY) / LD_X_sir
			else:
				self.beta = np.linalg.inv(LD_X_sir).dot(np.dot(self.theta, cor_ZY))
		elif self.sparse_reg.fit_flag:
			self.beta = self.sparse_reg.beta[-1]
		else:
			Z_aug = np.hstack((Z, self.X_sir))
			cov_aug = np.hstack((cor_ZY, np.dot(self.theta, cor_ZY)))
			LD_Z_aug = np.dot(Z_aug.T, Z_aug)
			self.sparse_reg.fit(LD_Z_aug, cov_aug)
			self.beta = self.sparse_reg.beta[-1]

	def fit_air(self, Z, X):
		self.cond_mean.fit(X=X[:,None], y=self.X_sir)
		pred_mean = self.cond_mean.predict(X=X[:,None])
		LD_Z_sum = np.sum(Z[:, :, np.newaxis] * Z[:, np.newaxis, :], axis=0)
		cross_mean_Z = np.sum(Z * pred_mean, axis=0)
		self.rho = (self.theta.dot(LD_Z_sum) * self.theta).sum(axis=1) / np.dot( self.theta, cross_mean_Z )

	def fit(self, Z, X, cor_ZY):
		## Stage 1: estimate theta based on SIR
		self.fit_sir(Z, X)
		## Stage 2: estimate beta via sparse regression
		self.fit_reg(Z, cor_ZY)
		## Estimate link function
		if self.fit_link:
			self.fit_air(Z, X)

	def link(self, X):
		if self.fit_link:
			if self.beta > 0:
				return self.rho * self.cond_mean.predict(X=X)
			else:
				return -self.rho * self.cond_mean.predict(X=X)
		else:
			print('You must fit a link function before evaluate it!')

	def CI_beta(Z, alpha):
		if self.fit_flag:
			cov_Z = np.cov(Z,rowvar=False)
			var_beta = 1. / (self.theta.dot(cov_Z) * self.theta).sum(axis=1)[0]
			delta_tmp = abs(norm.ppf((1. - alpha)/2)) * np.sqrt(var_beta) / np.sqrt(len(Z))
			beta_low = self.beta -  delta_tmp
			beta_high = self.beta + delta_tmp
			return [beta_low, beta_high]
		else:
			raise NameError('CI can only be generated after fit!')

