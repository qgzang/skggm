import numpy as np
from sklearn.base import BaseEstimator 
from sklearn.utils import check_array, as_float_array
from sklearn.utils.extmath import fast_logdet

import pyquic



def log_likelihood(covariance, precision):
    """Computes ...
    
    Parameters
    ----------
    covariance : 2D ndarray (n_features, n_features)
        Maximum Likelihood Estimator of covariance
    
    precision : 2D ndarray (n_features, n_features)
        The precision matrix of the covariance model to be tested
    
    Returns
    -------
    log-likelihood
    """
    
    # NOTE TO MANJARI: 
    # - scikit learn version does some additional scaling and normalization
    #   is this something we need to do?
    # - should this just be the same one used in Empirical Covariance?

    assert covariance.shape == precision.shape
    return np.trace(covariance * precision) - fast_logdet(precision)


def kl_loss(covariance, precision):
    """Computes the KL divergence between precision estimate (T_hat) and 
    reference precision (T).
    
    The loss is computed as:

        Trace(T_hat^{-1} * T) - log(T_hat^{-1} * T) - dim(T)

    so the function expects that the first parameter (covariance) is the 
    covariance estimate (T_hat^{-1}). 

    Parameters
    ----------
    covariance : 2D ndarray (n_features, n_features)
        Maximum Likelihood Estimator of covariance
    
    precision : 2D ndarray (n_features, n_features)
        The precision matrix of the covariance model to be tested
    
    Returns
    -------
    KL-divergence between precision_estimate and precision
    """
    assert covariance.shape == precision.shape
    dim, _ = precision.shape
    mul_cov_prec = covariance * precision
    return np.trace(mul_cov_prec) - np.log(mul_cov_prec) - dim


def quadratic_loss(covariance, precision):
    """Computes ...
    
    Parameters
    ----------
    covariance : 2D ndarray (n_features, n_features)
        Maximum Likelihood Estimator of covariance
    
    precision : 2D ndarray (n_features, n_features)
        The precision matrix of the covariance model to be tested
    
    Returns
    -------
    Quadratic loss
    """
    assert covariance.shape == precision.shape
    dim, _ = precision.shape
    return np.trace((covariance * precision - np.eye(dim))**2)


def quic(S, lam, mode='default', tol=1e-6, max_iter=1000, 
        Theta0=None, Sigma0=None, path=None, msg=0):
    """Fits the inverse covariance model according to the given training 
    data and parameters.

    Parameters
    -----------
    S : 2D ndarray, shape (n_features, n_features)
        Empirical covariance or correlation matrix.

    Other parameters described in `class InverseCovariance`.

    Returns
    -------
    Theta : 
    Sigma : 
    opt : 
    cputime : 
    iters : 
    dGap : 
    """
    assert mode in ['default', 'path', 'trace'],\
            'mode = \'default\', \'path\' or \'trace\'.'

    Sn, Sm = S.shape
    if Sn != Sm:
        raise ValueError("Input data must be square. S shape = {}".format(
                         S.shape))
        return

    # Regularization parameter matrix L.
    if isinstance(lam, float):
        _lam = np.empty((Sn, Sm))
        _lam[:] = lam
    else:
        assert L.shape == S.shape, 'lam, S shape mismatch.'
        _lam = as_float_array(lam, copy=False, force_all_finite=False)
 
    # Defaults.
    optSize = 1
    iterSize = 1
    if mode is "trace":
        optSize = max_iter

    # Default Theta0, Sigma0 when both are None.
    if Theta0 is None and Sigma0 is None:
        Theta0 = np.eye(Sn)
        Sigma0 = np.eye(Sn)

    assert Theta0 is not None,\
            'Theta0 and Sigma0 must both be None or both specified.'
    assert Sigma0 is not None,\
            'Theta0 and Sigma0 must both be None or both specified.'
    assert Theta0.shape == S.shape, 'Theta0, S shape mismatch.'
    assert Sigma0.shape == S.shape, 'Theta0, Sigma0 shape mismatch.'
    Theta0 = as_float_array(Theta0, copy=False, force_all_finite=False)
    Sigma0 = as_float_array(Sigma0, copy=False, force_all_finite=False)

    if mode is 'path':
        assert path is not None, 'Please specify the path scaling values.'
        path_len = len(path)
        optSize = path_len
        iterSize = path_len

        # Note here: memory layout is important:
        # a row of X/W holds a flattened Sn x Sn matrix,
        # one row for every element in _path_.
        Theta = np.empty((path_len, Sn * Sn))
        Theta[0,:] = Theta0.ravel()
        Sigma = np.empty((path_len, Sn * Sn))
        Sigma[0,:] = Sigma0.ravel()
    else:
        path = np.empty(1)
        path_len = len(path)

        Theta = np.empty(Theta0.shape)
        Theta[:] = Theta0
        Sigma = np.empty(Sigma0.shape)
        Sigma[:] = Sigma0
                    
    # Run QUIC.
    opt = np.zeros(optSize)
    cputime = np.zeros(optSize)
    dGap = np.zeros(optSize)
    iters = np.zeros(iterSize, dtype=np.uint32)
    pyquic.quic(mode, Sn, S, _lam, path_len, path, tol, msg, max_iter,
                Theta, Sigma, opt, cputime, iters, dGap)

    if optSize == 1:
        opt = opt[0]
        cputime = cputime[0]
        dGap = dGap[0]

    if iterSize == 1:
        iters = iters[0]

    return Theta, Sigma, opt, cputime, iters, dGap


class InverseCovariance(BaseEstimator):
    """
    Computes a sparse inverse covariance matrix estimation using quadratic 
    approximation. 

    The inverse covariance is estimated the sample covariance estimate 
    $S$ as an input such that: 

    $T_hat = max_{\Theta} logdet(Theta) - Trace(ThetaS) - \lambda|\Theta|_1 $

    Parameters
    -----------        
    lam : scalar or 2D ndarray, shape (n_features, n_features) (default=0.5)
        Regularization parameters per element of the inverse covariance matrix.
    
    mode : one of 'default', 'path', or 'trace'
        Computation mode.

    tol : float (default=1e-6)
        Convergence threshold.

    max_iter : int (default=1000)
        Maximum number of Newton iterations.

    Theta0 : 2D ndarray, shape (n_features, n_features) (default=None) 
        Initial guess for the inverse covariance matrix. If not provided, the 
        diagonal identity matrix is used.

    Sigma0 : 2D ndarray, shape (n_features, n_features) (default=None)
        Initial guess for the covariance matrix. If not provided the diagonal 
        identity matrix is used.

    path : array of floats (default=None)
        In "path" mode, an array of float values for scaling L.

    verbose : int (default=0)
        Verbosity level.

    method : one of 'quic', 'quicanddirty', 'ETC' (default=quic)

    Attributes
    ----------
    covariance_ : 2D ndarray, shape (n_features, n_features)
        Estimated covariance matrix

    precision_ : 2D ndarray, shape (n_features, n_features)
        Estimated pseudo-inverse matrix.

    opt_ :

    cputime_ :

    iters_ :    

    duality_gap_ :

    """
    def __init__(self, lam=0.5, mode='default', tol=1e-6, max_iter=1000,
                 Theta0=None, Sigma0=None, path=None, verbose=0, method='quic'):
        self.lam = lam
        self.mode = mode
        self.tol = tol
        self.max_iter = max_iter
        self.Theta0 = Theta0
        self.Sigma0 = Sigma0
        self.path = path
        self.verbose = verbose
        self.method = method

        self.covariance_ = None
        self.precision_ = None
        self.opt_ = None
        self.cputime_ = None
        self.iters_ = None
        self.duality_gap_ = None

        super(InverseCovariance, self).__init__()

    def fit(self, X, y=None, **fit_params):
        """Fits the inverse covariance model according to the given training 
        data and parameters.

        Parameters
        -----------
        X : 2D ndarray, shape (n_features, n_features)
            Input data.

        Returns
        -------
        self
        """
        X = check_array(X)
        X = as_float_array(X, copy=False, force_all_finite=False)

        # Get correlation coefficients.
        # Note: This could also be estimated via EmpiricalCovariance
        S = np.corrcoef(X)

        if self.method is 'quic':
            (self.precision_, self.covariance_, self.opt_, self.cputime_, 
            self.iters_, self.duality_gap_) = quic(S,
                                                self.lam,
                                                mode=self.mode,
                                                tol=self.tol,
                                                max_iter=self.max_iter,
                                                Theta0=self.Theta0,
                                                Sigma0=self.Sigma0,
                                                path=self.path,
                                                msg=self.verbose)
        else:
            raise NotImplementedError(
                "Only method='quic' has been implemented.")

        return self


    def score(self, X_test, y=None):
        """Computes the log-likelihood 

        # TODO: -log_likelihood instead?
       
        ----------
        X_test : array-like, shape = [n_samples, n_features]
            Test data of which we compute the likelihood, where n_samples is
            the number of samples and n_features is the number of features.
            X_test is assumed to be drawn from the same distribution than
            the data used in fit (including centering).
        
        y : not used.
        
        Returns
        -------
        res : float
            The likelihood of the data set with `self.covariance_` as an
            estimator of its covariance matrix.
        """
        # TODO: As Manjari mentioned, we should take input data to the interface
        #       and spit out results.  This should make this make more sense.

        # compute empirical covariance of the test set
        #test_cov = empirical_covariance(
        #    X_test - self.location_, assume_centered=True)
        
        return log_likelihood(test_cov, self.precision_)


    def error_norm(self, comp_prec, norm='frobenius', scaling=True, 
                   squared=True):
        """Computes the error between two inverse-covariance estimators 
        (i.e., over precision).
        
        Parameters
        ----------
        comp_prec : array-like, shape = [n_features, n_features]
            The precision to compare with.
                
        scaling : bool
            If True (default), the squared error norm is divided by n_features.
            If False, the squared error norm is not rescaled.

        norm : str
            The type of norm used to compute the error. Available error types:
            - 'frobenius' (default): sqrt(tr(A^t.A))
            - 'spectral': sqrt(max(eigenvalues(A^t.A))
            - 'kl': kl-divergence 
            - 'quadratic': qudratic loss
            where A is the error ``(comp_prec - self.precision_)``.
        
        squared : bool
            Whether to compute the squared error norm or the error norm.
            If True (default), the squared error norm is returned.
            If False, the error norm is returned.
        
        Returns
        -------
        The error between `self.precision_` and `comp_prec` 
        """
        # compute the error
        error = comp_prec - self.precision_
        
        # compute the error norm
        if norm == "frobenius":
            result = np.sum(error ** 2)
        elif norm == "spectral":
            result = np.amax(linalg.svdvals(np.dot(error.T, error)))
        elif norm == "kl":
            result = kl_loss(self.covariance_, comp_prec)
        elif norm == "quadratic":
            result = quadratic_loss(self.covariance_, comp_prec)
        else:
            raise NotImplementedError(
                "Only spectral and frobenius norms are implemented")

        # optionally scale the error norm
        if scaling:
            result = result / error.shape[0]
        
        # finally get either the squared norm or the norm
        if not squared:
            result = np.sqrt(squared_norm)

        return result

