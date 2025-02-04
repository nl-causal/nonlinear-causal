## Test invalid IVs
import numpy as np
# from sklearn.preprocessing import normalize
from sim_data import sim
from sklearn.preprocessing import StandardScaler
from scipy import stats
from sklearn.model_selection import train_test_split
from nl_causal.ts_models import _2SLS, _2SIR
from sklearn.preprocessing import power_transform, quantile_transform
from scipy.linalg import sqrtm
from nl_causal.linear_reg import L0_IC
from sklearn.linear_model import Lasso, ElasticNet, LinearRegression, LassoLarsIC, LassoCV

# normal AR(.5)
# ==================================================
# 'linear': beta0: 0.000, n: 10000, p: 50, bad_select: 143
# Rejection: 2sls: 0.050; RT_2sls: 0.051; SIR: 0.051

# ==================================================
# 'log': beta0: 0.000, n: 10000, p: 50, bad_select: 116
# Rejection: 2sls: 0.054; RT_2sls: 0.058; SIR: 0.055

# ==================================================
# 'cube-root': beta0: 0.000, n: 10000, p: 50, bad_select: 138
# Rejection: 2sls: 0.055; RT_2sls: 0.056; SIR: 0.055

# ==================================================
# inverse: beta0: 0.000, n: 10000, p: 50, bad_select: 153
# Rejection: 2sls: 0.056; RT_2sls: 0.068; SIR: 0.057

# ==================================================
# PL: beta0: 0.000, n: 10000, p: 50, bad_select: 164
# Rejection: 2sls: 0.055; RT_2sls: 0.057; SIR: 0.058

n, p = 10000, 50
df = {'true_beta': [], 'case': [], 'method': [], 'pct. of signif': []}

# theta0 = np.random.randn(p)
# for beta0 in [.0, .03, .05, .10]:
for beta0 in [.0]:
	# for case in ['linear', 'log', 'cube-root', 'inverse', 'piecewise_linear', 'quad']:
	for case in ['linear']:
		bad_select = 0
		p_value = []
		n_sim = 1000
		if beta0 > 0.:
			n_sim = 100
		for i in range(n_sim):
			theta0 = np.ones(p)
			theta0 = theta0 / np.sqrt(np.sum(theta0**2))
			alpha0 = np.zeros(p)
			alpha0[:5] = 1.
			# alpha0 = alpha0 / np.sqrt(np.sum(alpha0**2))
			Z, X, y, phi = sim(n, p, theta0, beta0, alpha0=alpha0, case=case, feat='normal')
			if abs(X).max() > 1e+8:
				continue
			## normalize Z, X, y
			center = StandardScaler(with_std=False)
			mean_X, mean_y = X.mean(), y.mean()
			Z, X, y = center.fit_transform(Z), X - mean_X, y - mean_y
			Z1, Z2, X1, X2, y1, y2 = train_test_split(Z, X, y, test_size=.5, random_state=42)
			## scale y
			y_scale = y2.std()
			y1 = y1 / y_scale
			y2 = y2 / y_scale
			y1 = y1 - y2.mean()
			y2 = y2 - y2.mean()
			# summary data
			n1, n2 = len(Z1), len(Z2)
			LD_Z1, cor_ZX1 = np.dot(Z1.T, Z1), np.dot(Z1.T, X1)
			LD_Z2, cor_ZY2 = np.dot(Z2.T, Z2), np.dot(Z2.T, y2)
			# print('True beta: %.3f' %beta0)

			Ks = range(int(p/2))
			## solve by 2sls
			reg_model = L0_IC(fit_intercept=False, alphas=10**np.arange(-1,3,.3),
							Ks=Ks, max_iter=50000, refit=False, find_best=False)
			LS = _2SLS(sparse_reg=reg_model)
			# LS = _2SCausal._2SLS(sparse_reg = SCAD_IC(fit_intercept=False, max_iter=10000))
			## Stage-1 fit theta
			LS.fit_theta(LD_Z1, cor_ZX1)
			## Stage-2 fit beta
			LS.fit_beta(LD_Z2, cor_ZY2, n2=n2)
			## generate CI for beta
			LS.test_effect(n2, LD_Z2, cor_ZY2)
			# print('alpha: %s' %(LS.alpha*y_scale))
			# print('est beta based on OLS: %.3f; p-value: %.5f' %(LS.beta*y_scale, LS.p_value))

			RT_X1 = power_transform(X1.reshape(-1,1)).flatten()
			# RT_X1 = quantile_transform(X1.reshape(-1,1), output_distribution='normal')
			reg_model = L0_IC(fit_intercept=False, alphas=10**np.arange(-1,3,.3), 
						Ks=Ks, max_iter=50000, refit=False, find_best=False)
			RT_cor_ZX1 = np.dot(Z1.T, RT_X1)
			RT_LS = _2SLS(sparse_reg=reg_model)
			## Stage-1 fit theta
			RT_LS.fit_theta(LD_Z1, RT_cor_ZX1)
			## Stage-2 fit beta
			RT_LS.fit_beta(LD_Z2, cor_ZY2, n2=n2)
			## generate CI for beta
			RT_LS.test_effect(n2, LD_Z2, cor_ZY2)
			# print('est beta based on PT_LS: %.3f; p-value: %.5f' %(RT_LS.beta*y_scale, RT_LS.p_value))

			## solve by SIR+LS
			reg_model = L0_IC(fit_intercept=False, alphas=10**np.arange(-1,3,.3), 
					Ks=Ks, max_iter=50000, refit=False, find_best=False)
			echo = _2SIR(sparse_reg=reg_model)
			## Stage-1 fit theta
			echo.fit_theta(Z1, X1)
			## Stage-2 fit beta
			echo.fit_beta(LD_Z2, cor_ZY2, n2=n2)
			## generate CI for beta
			echo.test_effect(n2, LD_Z2, cor_ZY2)
			# print('est beta based on 2SIR: %.3f; p-value: %.5f' %(echo.beta*y_scale, echo.p_value))
			
			data_in_slice_lst = [.1*n1, .2*n1, .3*n1, .4*n1, .5*n1]
			comb_pvalue, comb_beta = [], []
			for data_in_slice_tmp in data_in_slice_lst:
				num_slice = int(int(n1) / data_in_slice_tmp)
				reg_model = L0_IC(fit_intercept=False, alphas=10**np.arange(-1,3,.3), 
					Ks=Ks, max_iter=50000, refit=False, find_best=False)
				SIR = _2SIR(sparse_reg=reg_model, data_in_slice=data_in_slice_tmp)
				## Stage-1 fit theta
				SIR.fit_theta(Z1=Z1, X1=X1)
				## Stage-2 fit beta
				SIR.fit_beta(LD_Z2, cor_ZY2, n2)
				## generate CI for beta
				SIR.test_effect(n2, LD_Z2, cor_ZY2)
				comb_beta.append(SIR.beta)
				comb_pvalue.append(SIR.p_value)

			# correct_pvalue = min(len(data_in_slice_lst)*np.min(comb_pvalue), 1.0)
			comb_T = np.tan((0.5 - np.array(comb_pvalue))*np.pi).mean()
			correct_pvalue = min(.5 - np.arctan(comb_T)/np.pi, 1.0)
			
			if sorted(echo.best_model_) != sorted([0,1,2,3,4,50]):
				bad_select += 1
			
			p_value.append([LS.p_value, RT_LS.p_value, echo.p_value, correct_pvalue])
		p_value = np.array(p_value)

		rej_2SLS, rej_RT2SLS = len(p_value[p_value[:,0]<.05])/len(p_value), len(p_value[p_value[:,1]<.05])/len(p_value)
		rej_SIR, rej_CombSIR = len(p_value[p_value[:,2]<.05])/len(p_value), len(p_value[p_value[:,3]<.05])/len(p_value)

		df['true_beta'].extend([beta0]*5)
		df['case'].extend([case]*5)
		df['method'].extend(['2SLS', 'PT_2SLS', '2SIR', 'Comb-2SIR', 'signif level: .05'])
		df['pct. of signif'].extend([rej_2SLS, rej_RT2SLS, rej_SIR, rej_CombSIR, .05])

		print('='*40)
		print('case: %s; beta0: %.3f, n: %d, p: %d, bad_select: %d'%(case, beta0, n, p, bad_select))
		print('Rejection: 2sls: %.3f; RT_2sls: %.3f; SIR: %.3f; Comb-SIR: %.3f'
			  %(len(p_value[p_value[:,0]<.05])/len(p_value),
				len(p_value[p_value[:,1]<.05])/len(p_value),
				len(p_value[p_value[:,2]<.05])/len(p_value),
				len(p_value[p_value[:,3]<.05])/len(p_value)))

import pandas as pd
df = pd.DataFrame(df)

# import seaborn as sns
# import matplotlib.pyplot as plt
# sns.relplot(data=df, x="true_beta", y="pct. of signif", hue='method', style="method", col='case', kind='line', markers=True)
# plt.show()

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as stats
import seaborn as sns
from scipy.stats import rv_continuous
import statsmodels.api as sm
import random
from scipy.stats import beta

class neg_log_uniform(rv_continuous):
	"negative log uniform distribution"
	def _cdf(self, x):
		return 1. - 10**(-x)
NLU_rv = neg_log_uniform()

sm.qqplot(-np.log10(p_value[:,0]), dist=NLU_rv, line="45")