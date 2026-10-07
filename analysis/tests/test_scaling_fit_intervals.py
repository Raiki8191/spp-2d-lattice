import numpy as np
import pandas as pd
import pytest
from scipy.stats import t
from analysis.scaling_fit import _fit_row

@pytest.mark.parametrize("n",[4,7,8,9])
def test_log_slope_interval_uses_finite_degrees_of_freedom(n):
    L=np.array([8,12,16,24,32,48,64,96,128],float)[:n]
    values=L**-.2*np.exp(np.array([0,.04,-.02,.01,-.03,.02,.01,-.01,.025])[:n])
    row=_fit_row("C=1","P_after","Y",-1,8,pd.DataFrame({"L":L,"Y":values}))
    critical=(row["slope_ci95_high"]-row["slope"])/row["slope_standard_error"]
    assert critical == pytest.approx(t.ppf(.975,n-2),rel=1e-12)
    assert critical>1.96
    assert row["exponent_ci95_low"] == pytest.approx(-row["slope_ci95_high"])
