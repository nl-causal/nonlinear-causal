## test for elanet.py
import numpy as np
from sklearn.preprocessing import normalize
from sklearn.preprocessing import StandardScaler
from scipy import stats
from sklearn.datasets import make_regression

n, d = 1000, 10
X, y, beta_true = make_regression(n, d, coef=True)
X = np.hstack((X, X[:,:1]))
LD_X = np.dot(X.T, X)

from nonlinear_causal import _2SCausal
cov = np.sum(X*y[:,None], axis=0)
elasnet = _2SCausal.elasticSUM(lam=10.)
elasnet.fit(LD_X, cov)

print(elasnet.beta)
print(beta_true)

## test SCAD and MCP
import numpy as np
from scipy import stats
from sklearn.datasets import make_regression
import pycasso
n, d = 1000, 10
X, y, beta_true = make_regression(n, d, coef=True)
X = np.hstack((X, X[:,:1]))
s = pycasso.Solver(X, y, penalty='scad', lambdas=10**np.arange(-3,3,.1))
s.train()
s.plot()