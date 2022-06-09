import pandas as pd
import numpy as np
from statsmodels.stats.outliers_influence import variance_inflation_factor
from sklearn.feature_selection import VarianceThreshold

def variance_threshold_selector(data, threshold=0.05):
    """
    Remove low variance features.

    Parameters
    ----------
    X: {array-like, sparse matrix} of shape (n_samples, n_features)
        Feature matrix

    Returns
    -------
    X: return feature matrix by removing low variance features.

    Reference
    ---------
    https://stackoverflow.com/a/39813304/1956309
    """
    selector = VarianceThreshold(threshold)
    selector.fit(data)
    return data[data.columns[selector.get_support(indices=True)]]

def calculate_cor_(X, thresh=0.8, verbose=0):
    """
    Remove low-correlated features.

    Parameters
    ----------
    X: {array-like, sparse matrix} of shape (n_samples, n_features)
        Feature matrix

    Returns
    -------
    X: return feature matrix by removing low-correlated features.

    col: return the remaining columns.
    """
    cols = X.columns
    variables = np.array(range(X.shape[1]))
    for ix in range(len(variables)):
        if ix >= len(variables):
            break
        cor_tmp = np.zeros(len(variables))
        cor_tmp[ix+1:] = X.iloc[:,variables].iloc[:,ix+1:].corrwith(X.iloc[:,variables].iloc[:,ix]).values
        if max(cor_tmp) > thresh:
            variables = variables[cor_tmp<thresh]
            # print(len(variables))
    if verbose:
        print('Remaining variables:')
        print(X.columns[variables])
    cols_new = cols[variables]
    return X.iloc[:, variables], cols_new
    

def calculate_vif_(X, thresh=2.5, verbose=0):
    """
    Remove multicollinearity features.

    Parameters
    ----------
    X: {array-like, sparse matrix} of shape (n_samples, n_features)
        Feature matrix

    Returns
    -------
    X: return feature matrix by removing multicollinearity features.

    col: return the remaining columns.
    """
    cols = X.columns
    variables = list(range(X.shape[1]))
    dropped = True
    while dropped:
        dropped = False
        vif = [variance_inflation_factor(X.iloc[:, variables].values, ix)
                for ix in range(X.iloc[:, variables].shape[1])]

        maxloc = vif.index(max(vif))
        if max(vif) > thresh:
            if verbose:
                print('dropping \'' + X.iloc[:, variables].columns[maxloc] +
                        '\' at index: ' + str(maxloc))
            del variables[maxloc]
            dropped = True
    if verbose:
        print('Remaining variables:')
        print(X.columns[variables])
    cols_new = cols[variables]
    return X.iloc[:, variables], cols_new
