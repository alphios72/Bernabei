import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def calculate_convenience_score(history_data, current_price):
    """
    Calculates the Convenience Score (S) based on the provided algorithm.
    
    params:
    - history_data: List of dicts or objects with 'timestamp' and 'price'
    - current_price: Float, current price p0
    """
    if not history_data:
        return 0.0
    
    # 0. Convert to DataFrame
    df = pd.DataFrame(history_data)
    if 'timestamp' not in df.columns or 'price' not in df.columns:
        return 0.0
        
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values('timestamp')
    df = df.set_index('timestamp')
    
    # Current time t0
    t0 = datetime.utcnow()
    
    # 1) Preprocess
    # Resample to daily p(t) using min (conservative) or median
    # We use min as valid price for that day
    daily = df['price'].resample('D').min().dropna()
    
    if daily.empty:
        return 0.0
        
    # Remove outliers (robust) - Simple IQR method
    Q1 = daily.quantile(0.25)
    Q3 = daily.quantile(0.75)
    IQR = Q3 - Q1
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    # Filter, but ensure we don't remove everything
    clean_daily = daily[(daily >= lower_bound) & (daily <= upper_bound)]
    if clean_daily.empty:
        clean_daily = daily # Fallback if everything was an outlier
        
    # 2) Select last N=365 days
    N_days = 365
    cutoff_date = t0 - timedelta(days=N_days)
    series = clean_daily[clean_daily.index >= cutoff_date]
    
    if series.empty:
        return 0.0
        
    # Params
    W_days = 60
    tau = 90
    d_max = 0.25
    v0 = 0.03
    
    # 3) Compute weights w_i
    # w_i = exp(-(t0 - t_i)/tau)
    # seasonal_weight ignored for now (assumed 1) unless specified
    
    dates = series.index
    # Ensure we are working with values, not index operations that might return Index
    days_diff = (t0 - dates).days
    # keys to use for weights
    weights = np.exp(-days_diff / tau)
    
    # If weights is a pandas Index or Series with index, it might cause issues. 
    # Convert to pure numpy array to be safe.
    if hasattr(weights, 'values'):
        weights = weights.values
    else:
        weights = np.array(weights)
    
    # A) Weighted percentile q
    # q = sum_{p_i <= p0} w_i / sum w_i
    
    # p0 is current_price
    mask = series <= current_price
    weighted_sum_lower = weights[mask].sum()
    total_weights = weights.sum()
    
    if total_weights == 0:
        q = 1.0
    else:
        q = weighted_sum_lower / total_weights
        
    S_A = 10 * (1 - q)
    
    # B) Estimate baseline B(t)
    # Using EMA with span corresponding to roughly 3 months?
    # Or simple moving average. Let's use EMA span=90 days
    ema = series.ewm(span=90).mean()
    if ema.empty:
        B0 = current_price
    else:
        B0 = ema.iloc[-1]
        
    if B0 == 0: B0 = 1.0 # Avoid div/0
    
    d = (B0 - current_price) / B0
    # clip(d/d_max, 0, 1)
    val_b = max(0, min(d/d_max, 1))
    S_B = 10 * val_b
    
    # C) Range analysis last W=60 days
    cutoff_W = t0 - timedelta(days=W_days)
    last_W_series = series[series.index >= cutoff_W]
    
    if last_W_series.empty:
        # If no recent data, assume worst case for range? or neutral?
        # Let's say neutral S_C = 5
        S_C = 5.0
        # Volatility needs data too
        R = 1.0 
    else:
        mW = last_W_series.min()
        MW = last_W_series.max()
        
        if MW == mW:
            r = 0.5
        else:
            r = (MW - current_price) / (MW - mW)
            
        S_C = 10 * r
        
        # R) Volatility v = MAD(p - B) / median(p) over last W
        # Re-calculate baseline for this window? Or use main EMA?
        # Let's use main EMA aligned to this window
        window_ema = ema[ema.index >= cutoff_W]
        # Align series
        aligned_series = last_W_series.loc[window_ema.index]
        
        if aligned_series.empty:
            v = 0
        else:
            diffs = (aligned_series - window_ema).abs()
            mad = diffs.median() # MAD is median absolute deviation
            med_p = aligned_series.median()
            
            if med_p == 0:
                v = 0
            else:
                v = mad / med_p
                
        # coverage_factor? 
        # If we have very few points, reduce reliability.
        # Let's assume 1.0 if we have at least 5 points
        coverage_factor = 1.0 if len(last_W_series) > 5 else 0.5
        
        R = np.exp(-v/v0) * coverage_factor

    # Optional P skipped as requested ("optional")
    P = 0
    lambda_param = 0 # if P is 0 this doesn't matter
    
    # S_base = 0.45*S_A + 0.35*S_B + 0.20*S_C
    S_base = 0.45 * S_A + 0.35 * S_B + 0.20 * S_C
    
    # S = clip(R*S_base - lambda*P, 0, 10)
    S_final = max(0, min(R * S_base, 10))
    
    return round(S_final, 1)
