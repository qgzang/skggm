import sys
import numpy as np
from sklearn.datasets import make_sparse_spd_matrix

sys.path.append('..')
from inverse_covariance import QuicGraphLasso
from inverse_covariance.plot_util import trace_plot 


def make_data(n_samples, n_features):
    prng = np.random.RandomState(1)
    prec = make_sparse_spd_matrix(n_features, alpha=.98,
                              smallest_coef=.4,
                              largest_coef=.7,
                              random_state=prng)
    cov = np.linalg.inv(prec)
    d = np.sqrt(np.diag(cov))
    cov /= d
    cov /= d[:, np.newaxis]
    prec *= d
    prec *= d[:, np.newaxis]
    X = prng.multivariate_normal(np.zeros(n_features), cov, size=n_samples)
    X -= X.mean(axis=0)
    X /= X.std(axis=0)
    return X, cov, prec


def show_quic_coefficient_trace(X):
    path = np.logspace(np.log10(0.01), np.log10(1.0), num=50, endpoint=True)[::-1]
    estimator = QuicGraphLasso(
            lam=1.0,
            path=path,
            mode='path')
    estimator.fit(X)
    trace_plot(estimator.precision_, estimator.path_)


if __name__ == "__main__":
    n_samples = 10
    n_features = 5
    X, cov, prec = make_data(n_samples, n_features)
    show_quic_coefficient_trace(X)
