import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.stats.stattools import durbin_watson
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
import os

warnings.filterwarnings('ignore')

OUTPUT_DIR = "/Users/rohith.devarasetty/Documents/Cursor/AI Visibility Analysis"

# ---------------------------------------------------------------------------
# RAW DATA  (daily grain from Google Sheet)
# Columns: date, ai_visibility_score, direct_visits_raw, direct_enrollments,
#          brand_spend, nb_spend
# ---------------------------------------------------------------------------
RAW_ROWS = [
    ("2025-06-01", 53.57, "214K", 3457,  39151,  71367),
    ("2025-06-02", 50.58, "211K", 4090,  43969,  89109),
    ("2025-06-03", 50.44, "136K", 3915,  42754, 109313),
    ("2025-06-04", 54.01, "131K", 3912,  43384,  87003),
    ("2025-06-05", 53.36, "134K", 3712,  41827,  96736),
    ("2025-06-06", 57.64, "116K", 3546,  39860, 103794),
    ("2025-06-07", 50.69, "103K", 2965,  34044,  89938),
    ("2025-06-08", 55.86,  "94K", 2975,  31477,  84953),
    ("2025-06-09", 55.36, "106K", 3801,  36912,  89410),
    ("2025-06-10", 56.55, "106K", 3603,  36785,  92520),
    ("2025-06-11", 56.87, "115K", 3830,  41251, 100227),
    ("2025-06-12", 68.33, "117K", 3771,  42809, 111754),
    ("2025-06-13", 65.71, "110K", 3768,  37637, 114851),
    ("2025-06-14", 47.50,  "95K", 3237,  31043, 102035),
    ("2025-06-15", 46.43,  "87K", 3047,  27570, 103514),
    ("2025-06-16", 52.86, "109K", 3830,  36658, 109969),
    ("2025-06-17", 46.10, "120K", 3998,  37992, 117397),
    ("2025-06-18", 47.16, "136K", 3963,  39196, 106299),
    ("2025-06-19", 44.33, "121K", 3764,  35967, 103725),
    ("2025-06-20", 48.03, "114K", 3927,  36165, 151180),
    ("2025-06-21", 42.94, "176K", 3365, 148972, 116816),
    ("2025-06-22", 46.77, "101K", 3533,  28949, 106237),
    ("2025-06-23", 48.67, "111K", 4178,  30796, 107328),
    ("2025-06-24", 54.17, "110K", 4270,  33162,  95381),
    ("2025-06-25", 46.88, "125K", 4457,  41570,  98777),
    ("2025-06-26", 47.39, "123K", 4033,  53251, 108292),
    ("2025-06-27", 44.66, "121K", 4162,  61717, 113487),
    ("2025-06-28", 49.24, "107K", 3575,  54737,  98831),
    ("2025-06-29", 46.10,  "93K", 3685,  50117, 101056),
    ("2025-06-30", 50.14, "112K", 4365,  65759, 115282),
    ("2025-07-01", 47.97, "254K", 4901,  79435, 116502),
    ("2025-07-02", 51.46, "182K", 4028,  74796, 110093),
    ("2025-07-03", 50.93, "137K", 3897,  74230, 101938),
    ("2025-07-04", 51.90, "112K", 2941,  51380,  73259),
    ("2025-07-05", 51.28, "121K", 3155,  52474,  61239),
    ("2025-07-06", 49.56, "108K", 3689,  55963,  77553),
    ("2025-07-07", 47.60, "117K", 4242,  72030,  83537),
    ("2025-07-08", 49.77, "110K", 4235,  74634, 110455),
    ("2025-07-09", 48.91, "119K", 3593,  71885, 107974),
    ("2025-07-10", 49.45, "117K", 3484,  64280,  47234),
    ("2025-07-11", 49.18, "120K", 3511,  63822,  44017),
    ("2025-07-12", 45.45, "105K", 3129,  57959, 125411),
    ("2025-07-13", 47.95,  "98K", 3118,  52300,  71008),
    ("2025-07-14", 46.23, "137K", 4083,  66014,  46979),
    ("2025-07-15", 50.21, "119K", 4257,  65712,  86886),
    ("2025-07-16", 49.21, "123K", 3901,  76152, 195019),
    ("2025-07-17", 52.67, "131K", 4007,  76784, 183764),
    ("2025-07-18", 48.83, "125K", 3580,  69290, 176102),
    ("2025-07-19", 53.38, "104K", 3476,  64152, 154190),
    ("2025-07-20", 49.81,  "97K", 3328,  56915, 131667),
    ("2025-07-21", 48.07, "115K", 3738,  80285, 154127),
    ("2025-07-22", 48.06, "112K", 3895,  66830, 132218),
    ("2025-07-23", 48.48, "127K", 3704,  76851, 126928),
    ("2025-07-24", 49.36, "122K", 3817,  72325, 121245),
    ("2025-07-25", 49.37, "127K", 3487,  68582, 120184),
    ("2025-07-26", 50.56, "108K", 3383,  61214, 113561),
    ("2025-07-27", 53.51, "100K", 3034,  53652, 111390),
    ("2025-07-28", 51.30, "123K", 3944,  80115, 136957),
    ("2025-07-29", 54.88, "127K", 3876,  83117, 142750),
    ("2025-07-30", 57.16, "127K", 4459,  83435, 125877),
    ("2025-07-31", 57.77, "136K", 4535,  81960, 131203),
    ("2025-08-01", 47.65, "239K", 4054,  80693, 127851),
    ("2025-08-02", 49.28, "149K", 3435,  61879, 121684),
    ("2025-08-03", 50.63, "122K", 3166,  62031,  96825),
    ("2025-08-04", 49.81, "128K", 3785,  71576, 113208),
    ("2025-08-05", 49.56, "151K", 3731,  79250, 105900),
    ("2025-08-06", 49.10, "130K", 3595,  81594, 105240),
    ("2025-08-07", 49.99, "124K", 3612,  76556, 107760),
    ("2025-08-08", 35.67, "124K", 3678,  80763, 109154),
    ("2025-08-09", 45.85, "104K", 3272,  63175, 106681),
    ("2025-08-10", 49.07,  "96K", 3051,  67080,  98131),
    ("2025-08-11", 44.67, "110K", 3463,  78211, 138517),
    ("2025-08-12", 47.26, "107K", 3605,  83334, 124062),
    ("2025-08-13", 52.23, "115K", 3764,  80365, 124097),
    ("2025-08-14", 50.57, "121K", 3538,  85478, 129216),
    ("2025-08-15", 49.59, "131K", 3530,  77162, 129237),
    ("2025-08-16", 49.96, "126K", 3231,  60278, 126917),
    ("2025-08-17", 47.49, "122K", 3255,  67304, 122902),
    ("2025-08-18", 53.05, "171K", 3739,  83507, 148208),
    ("2025-08-19", 48.57, "185K", 3796,  79581, 154186),
    ("2025-08-20", 49.90, "217K", 3642,  80105, 146258),
    ("2025-08-21", 50.60, "233K", 3614,  68694, 117993),
    ("2025-08-22", 50.48, "209K", 3639,  54141, 100040),
    ("2025-08-23", 52.88, "166K", 3304,  44930,  97546),
    ("2025-08-24", 53.95, "145K", 3544,  41421,  98092),
    ("2025-08-25", 52.58, "177K", 3823,  55520, 109692),
    ("2025-08-26", 49.58, "161K", 3669,  58017, 123891),
    ("2025-08-27", 48.67, "175K", 3662,  60621, 108650),
    ("2025-08-28", 47.91, "173K", 3577,  58023, 105153),
    ("2025-08-29", 46.19, "155K", 4141,  56482, 108994),
    ("2025-08-30", 47.05, "133K", 3378,  45887,  94987),
    ("2025-08-31", 51.76, "131K", 3809,  42287,  81604),
    ("2025-09-01", 50.54, "334K", 3993,  47129, 109681),
    ("2025-09-02", 51.49, "235K", 4264,  56605, 138050),
    ("2025-09-03", 51.09, "201K", 4217,  59376, 136606),
    ("2025-09-04", 49.42, "173K", 4093,  57739, 137344),
    ("2025-09-05", 49.56, "158K", 4134,  57753, 130403),
    ("2025-09-06", 47.68, "125K", 3406,  54368, 109016),
    ("2025-09-07", 49.66, "117K", 3541,  51373, 120676),
    ("2025-09-08", 50.03, "140K", 4075,  65211, 130550),
    ("2025-09-09", 50.17, "137K", 3791,  63456, 143519),
    ("2025-09-10", 46.20, "146K", 3516,  62813, 137347),
    ("2025-09-11", 47.28, "139K", 3796,  58727, 147738),
    ("2025-09-12", 46.87, "133K", 3859,  58788, 116359),
    ("2025-09-13", 47.33, "114K", 3485,  47874,  93194),
    ("2025-09-14", 46.00, "111K", 3727,  45467,  96435),
    ("2025-09-15", 42.20, "126K", 4176,  55747, 153379),
    ("2025-09-16", 45.86, "168K", 4047,  61541, 142567),
    ("2025-09-17", 44.64, "164K", 4301,  65019, 141738),
    ("2025-09-18", 40.91, "180K", 3831,  60764, 110896),
    ("2025-09-19", 43.93, "151K", 4054,  61252, 126572),
    ("2025-09-20", 43.73, "127K", 3418,  51578,  79519),
    ("2025-09-21", 42.90, "113K", 3479,  46527,  85188),
    ("2025-09-22", 42.66, "130K", 4113,  56038,  98391),
    ("2025-09-23", 39.35, "139K", 3864,  60937, 112628),
    ("2025-09-24", 45.03, "146K", 4002,  62252, 133979),
    ("2025-09-25", 42.64, "149K", 4070,  64014, 116709),
    ("2025-09-26", 44.15, "140K", 3736,  63287, 104650),
    ("2025-09-27", 40.31, "121K", 3662,  43395,  70396),
    ("2025-09-28", 43.51, "113K", 3554,  43111,  71325),
    ("2025-09-29", 45.03, "143K", 4222,  60733,  87130),
    ("2025-09-30", 46.67, "154K", 4047,  63290,  93208),
    ("2025-10-01", 40.99, "293K", 4685,  66411,  97178),
    ("2025-10-02", 41.00, "194K", 4096,  59464,  83832),
    ("2025-10-03", 45.47, "152K", 3695,  57462, 116970),
    ("2025-10-04", 42.75, "122K", 3304,  49813, 118140),
    ("2025-10-05", 44.76, "121K", 3324,  47667, 108093),
    ("2025-10-06", 40.58, "138K", 3607,  59757, 111918),
    ("2025-10-07", 37.42, "147K", 3699,  60561, 115738),
    ("2025-10-08", 33.02, "159K", 3674,  61624, 101520),
    ("2025-10-09", 32.79, "156K", 3605,  72364, 118722),
    ("2025-10-10", 35.40, "137K", 3588,  67206,  99882),
    ("2025-10-11", 33.09, "121K", 3228,  59940,  57970),
    ("2025-10-12", 34.40, "114K", 3160,  57854,  48697),
    ("2025-10-13", 32.16, "125K", 3537,  67228,  54770),
    ("2025-10-14", 34.91, "140K", 4045,  76579,  82062),
    ("2025-10-15", 33.28, "195K", 3758,  81166, 132953),
    ("2025-10-16", 40.45, "156K", 3436,  77822, 100428),
    ("2025-10-17", 35.89, "134K", 3379,  99673,  94375),
    ("2025-10-18", 32.02, "113K", 3101,  93844,  72587),
    ("2025-10-19", 35.48, "107K", 2785,  91623, 104836),
    ("2025-10-20", 32.88, "177K", 3190, 212664, 150203),
    ("2025-10-21", 32.74, "133K", 3550,  58922, 161065),
    ("2025-10-22", 33.74, "157K", 3639,  60939, 163188),
    ("2025-10-23", 35.64, "195K", 3518,  63966, 156871),
    ("2025-10-24", 36.31, "185K", 3313,  58660, 132714),
    ("2025-10-25", 34.66, "141K", 2835,  48409, 108519),
    ("2025-10-26", 33.92, "131K", 2907,  48422, 106234),
    ("2025-10-27", 34.01, "163K", 3401,  54490, 139574),
    ("2025-10-28", 34.13, "199K", 3490,  53995, 142776),
    ("2025-10-29", 34.36, "236K", 3616,  55934, 125777),
    ("2025-10-30", 33.26, "245K", 3793,  57666, 148117),
    ("2025-10-31", 33.16, "348K", 3086,  56996, 143185),
    ("2025-11-01", 35.00, "401K", 2854,  53249, 154608),
    ("2025-11-02", 33.82, "249K", 3075,  50364, 163918),
    ("2025-11-03", 33.87, "226K", 3650,  57320, 220562),
    ("2025-11-04", 29.51, "215K", 3628,  58810, 187537),
    ("2025-11-05", 29.91, "232K", 3503,  63075, 199556),
    ("2025-11-06", 31.22, "203K", 3558,  65187, 182110),
    ("2025-11-07", 33.29, "213K", 3627,  56442, 175508),
    ("2025-11-08", 33.43, "171K", 3183,  51714, 136130),
    ("2025-11-09", 30.29, "157K", 3228,  48910, 119343),
    ("2025-11-10", 32.87, "187K", 3851,  60217, 166162),
    ("2025-11-11", 31.28, "170K", 3841,  57787, 147989),
    ("2025-11-12", 35.41, "200K", 3716,  64823, 134094),
    ("2025-11-13", 29.51, "194K", 4020,  68292, 154675),
    ("2025-11-14", 35.64, "191K", 3738,  73074, 144040),
    ("2025-11-15", 34.44, "216K", 3474,  62131, 135741),
    ("2025-11-16", 35.48, "153K", 3391,  57455, 128284),
    ("2025-11-17", 37.93, "197K", 3854,  73367, 152236),
    ("2025-11-18", 36.93, "164K", 3530,  76522, 159454),
    ("2025-11-19", 37.05, "253K", 3797,  65771, 110791),
    ("2025-11-20", 39.22, "262K", 3857,  64082,  96379),
    ("2025-11-21", 38.19, "177K", 3846,  59054,  99762),
    ("2025-11-22", 34.37, "147K", 3287,  52909, 106154),
    ("2025-11-23", 36.08, "135K", 3217,  48237, 147884),
    ("2025-11-24", 27.24, "191K", 3699,  65098, 115353),
    ("2025-11-25", 36.44, "198K", 3862,  62706, 117318),
    ("2025-11-26", 35.48, "169K", 3669,  60936, 140222),
    ("2025-11-27", 34.33, "130K", 3045,  46106,  82586),
    ("2025-11-28", 35.54, "155K", 3899,  62621, 112280),
    ("2025-11-29", 34.24, "144K", 3608,  58006, 121734),
    ("2025-11-30", 35.27, "137K", 3337,  56082, 129242),
    ("2025-12-01", 36.68, "320K", 4585,  69058, 174888),
    ("2025-12-02", 35.56, "235K", 4162,  67448, 184582),
    ("2025-12-03", 37.23, "204K", 4255,  69666, 144620),
    ("2025-12-04", 33.79, "181K", 3933,  67079, 137681),
    ("2025-12-05", 32.98, "191K", 3715,  68685, 162621),
    ("2025-12-06", 34.10, "147K", 3328,  52038, 116789),
    ("2025-12-07", 33.16, "133K", 3484,  48059,  86313),
    ("2025-12-08", 33.52, "155K", 3772,  60782, 130796),
    ("2025-12-09", 34.19, "154K", 3856,  55252, 128521),
    ("2025-12-10", 32.48, "159K", 3809,  59177, 131781),
    ("2025-12-11", 34.94, "159K", 3841,  60783,  96315),
    ("2025-12-12", 36.55, "146K", 3615,  58695, 110013),
    ("2025-12-13", 36.06, "137K", 3058,  50937,  93000),
    ("2025-12-14", 35.73, "121K", 3055,  50311,  69020),
    ("2025-12-15", 35.44, "172K", 3642,  58432, 129543),
    ("2025-12-16", 36.85, "182K", 3621,  63710, 112832),
    ("2025-12-17", 39.21, "183K", 3606,  63966, 105312),
    ("2025-12-18", 39.40, "172K", 3642,  63053,  94185),
    ("2025-12-19", 38.56, "177K", 3491,  57888,  90547),
    ("2025-12-20", 40.00, "156K", 3120,  51245,  69831),
    ("2025-12-21", 40.91, "149K", 3022,  48185,  73295),
    ("2025-12-22", 38.32, "191K", 3410,  57721,  95270),
    ("2025-12-23", 38.28, "210K", 3533,  62226,  95903),
    ("2025-12-24", 39.91, "180K", 3073,  52738,  57351),
    ("2025-12-25", 38.92, "136K", 2612,  40448,  47733),
    ("2025-12-26", 38.04, "154K", 3340,  54905,  97455),
    ("2025-12-27", 40.01, "144K", 3138,  50596,  78269),
    ("2025-12-28", 38.43, "139K", 3174,  49152,  86546),
    ("2025-12-29", 39.70, "176K", 3789,  64131,  96817),
    ("2025-12-30", 40.01, "175K", 3757,  67719, 100225),
    ("2025-12-31", 39.70, "186K", 3394,  63089, 103369),
    ("2026-01-01", 38.63, "277K", 3349,  60297, 114584),
    ("2026-01-02", 40.25, "211K", 3826,  67321, 108574),
    ("2026-01-03", 41.24, "159K", 3544,  61223, 118394),
    ("2026-01-04", 40.34, "141K", 3385,  57795, 118731),
    ("2026-01-05", 40.40, "159K", 3843,  67819, 174751),
    ("2026-01-06", 38.38, "158K", 3631,  68272, 148455),
    ("2026-01-07", 38.30, "165K", 3577,  67063, 141760),
    ("2026-01-08", 38.80, "158K", 3597,  63952, 133460),
    ("2026-01-09", 39.45, "149K", 3702,  63557, 159494),
    ("2026-01-10", 39.74, "135K", 3361,  56324, 109407),
    ("2026-01-11", 39.39, "122K", 3330,  52217,  94527),
    ("2026-01-12", 38.78, "150K", 3860,  62312, 112285),
]

# ---------------------------------------------------------------------------
# US MONTHLY UNEMPLOYMENT RATE  (BLS official, seasonally adjusted)
# Source: BLS Employment Situation news releases
# Oct-2025 not collected due to federal government shutdown → interpolated
# ---------------------------------------------------------------------------
UNEMPLOYMENT_RATE = {
    6:  4.1,   # June 2025
    7:  4.2,   # July 2025
    8:  4.3,   # August 2025
    9:  4.4,   # September 2025
    10: 4.5,   # October 2025 – interpolated (no survey due to shutdown)
    11: 4.6,   # November 2025
    12: 4.4,   # December 2025
    1:  4.3,   # January 2026
}

# Month key: (year, month) for safety across year boundary
UNEMPLOYMENT_RATE_FULL = {
    (2025, 6):  4.1,
    (2025, 7):  4.2,
    (2025, 8):  4.3,
    (2025, 9):  4.4,
    (2025, 10): 4.5,
    (2025, 11): 4.6,
    (2025, 12): 4.4,
    (2026, 1):  4.3,
}


# ---------------------------------------------------------------------------
# DATA PREPARATION
# ---------------------------------------------------------------------------
def parse_visits(v: str) -> float:
    v = str(v).strip().upper().replace(",", "")
    if v.endswith("M"):
        return float(v[:-1]) * 1_000_000
    if v.endswith("K"):
        return float(v[:-1]) * 1_000
    return float(v)


df = pd.DataFrame(RAW_ROWS, columns=[
    "date", "ai_visibility", "direct_visits_raw",
    "direct_enrollments", "brand_spend", "nb_spend"
])
df["date"] = pd.to_datetime(df["date"])
df["direct_visits"] = df["direct_visits_raw"].apply(parse_visits)
df = df.drop(columns=["direct_visits_raw"]).sort_values("date").reset_index(drop=True)

# Standardise spend to $000s
df["brand_spend_k"] = df["brand_spend"] / 1_000
df["nb_spend_k"]    = df["nb_spend"]    / 1_000

# Map unemployment rate by (year, month)
df["unemployment_rate"] = df["date"].apply(
    lambda d: UNEMPLOYMENT_RATE_FULL.get((d.year, d.month), np.nan)
)

# Seasonality controls
df["day_of_week"] = df["date"].dt.dayofweek
df["is_weekend"]  = (df["day_of_week"] >= 5).astype(int)
df["month"]       = df["date"].dt.month
df["month_sin"]   = np.sin(2 * np.pi * df["month"] / 12)
df["month_cos"]   = np.cos(2 * np.pi * df["month"] / 12)

print(f"Raw dataset: {len(df)} rows\n")

# ---------------------------------------------------------------------------
# OUTLIER REMOVAL  (IQR method on dependent variables + brand_spend_k)
# Flags rows where any key variable falls outside  Q1 - 1.5*IQR … Q3 + 1.5*IQR
# ---------------------------------------------------------------------------
def iqr_mask(series: pd.Series) -> pd.Series:
    Q1, Q3 = series.quantile(0.25), series.quantile(0.75)
    IQR = Q3 - Q1
    return (series >= Q1 - 1.5 * IQR) & (series <= Q3 + 1.5 * IQR)

mask_visits  = iqr_mask(df["direct_visits"])
mask_enroll  = iqr_mask(df["direct_enrollments"])
mask_bspend  = iqr_mask(df["brand_spend_k"])

mask_clean = mask_visits & mask_enroll & mask_bspend
df_clean = df[mask_clean].copy().reset_index(drop=True)

n_removed = len(df) - len(df_clean)
outliers  = df[~mask_clean][["date", "direct_visits", "direct_enrollments", "brand_spend_k"]]
print(f"Outliers removed: {n_removed} rows")
print(outliers.to_string(index=False))
print(f"\nClean dataset: {len(df_clean)} rows\n")

# Lag variables (applied to clean dataset, in date order)
for lag in [1, 2, 3]:
    df_clean[f"ai_vis_lag{lag}"]        = df_clean["ai_visibility"].shift(lag)
    df_clean[f"brand_spend_k_lag{lag}"] = df_clean["brand_spend_k"].shift(lag)
    df_clean[f"nb_spend_k_lag{lag}"]    = df_clean["nb_spend_k"].shift(lag)

df_m = df_clean.dropna().reset_index(drop=True)
print(f"Modelling dataset (after lag NaN drop): {len(df_m)} rows\n")

print(df_m[["ai_visibility", "direct_visits", "direct_enrollments",
            "brand_spend_k", "nb_spend_k", "unemployment_rate"]].describe().round(1))


# ---------------------------------------------------------------------------
# HELPER
# ---------------------------------------------------------------------------
def coef_table(result, title):
    print(f"\n{'='*68}")
    print(f"  {title}")
    print(f"{'='*68}")
    print(f"  R²={result.rsquared:.3f}  Adj-R²={result.rsquared_adj:.3f}  "
          f"F={result.fvalue:.1f}  p(F)={result.f_pvalue:.4f}  "
          f"n={int(result.nobs)}")
    print(f"  Durbin-Watson: {durbin_watson(result.resid):.2f}")
    print(f"{'-'*68}")
    print(f"  {'Variable':<30} {'Coef':>10} {'Std Err':>10} {'t':>8} {'p':>8}  Sig")
    print(f"{'-'*68}")
    for var in result.params.index:
        c   = result.params[var]
        se  = result.bse[var]
        t   = result.tvalues[var]
        p   = result.pvalues[var]
        sig = "***" if p < 0.001 else ("**" if p < 0.01 else ("*" if p < 0.05 else ("." if p < 0.1 else "")))
        print(f"  {var:<30} {c:>10.3f} {se:>10.3f} {t:>8.2f} {p:>8.4f}  {sig}")
    print(f"{'='*68}")
    ci = result.conf_int()
    ci.columns = ["CI_2.5%", "CI_97.5%"]
    print("\n  95% Confidence Intervals:")
    print(ci.round(3).to_string())


FEATURES_WITH_UE   = ["ai_visibility", "brand_spend_k", "nb_spend_k",
                      "unemployment_rate", "is_weekend", "month_sin", "month_cos"]
FEATURES_NO_UE     = ["ai_visibility", "brand_spend_k", "nb_spend_k",
                      "is_weekend", "month_sin", "month_cos"]
LAG_FEATURES_NO_UE = ["ai_vis_lag1", "ai_vis_lag2", "ai_vis_lag3",
                      "brand_spend_k_lag1", "nb_spend_k_lag1",
                      "is_weekend", "month_sin", "month_cos"]
LAG_FEATURES_UE    = ["ai_vis_lag1", "ai_vis_lag2", "ai_vis_lag3",
                      "brand_spend_k_lag1", "nb_spend_k_lag1",
                      "unemployment_rate", "is_weekend", "month_sin", "month_cos"]

Yv = df_m["direct_visits"]
Ye = df_m["direct_enrollments"]

# ---------------------------------------------------------------------------
# MODELS WITH UNEMPLOYMENT RATE
# ---------------------------------------------------------------------------
Xv_ue  = sm.add_constant(df_m[FEATURES_WITH_UE])
Xe_ue  = sm.add_constant(df_m[FEATURES_WITH_UE])
Xvl_ue = sm.add_constant(df_m[LAG_FEATURES_UE])
Xel_ue = sm.add_constant(df_m[LAG_FEATURES_UE])

model_visits_ue      = sm.OLS(Yv, Xv_ue).fit(cov_type="HC3")
model_enroll_ue      = sm.OLS(Ye, Xe_ue).fit(cov_type="HC3")
model_visits_lag_ue  = sm.OLS(Yv, Xvl_ue).fit(cov_type="HC3")
model_enroll_lag_ue  = sm.OLS(Ye, Xel_ue).fit(cov_type="HC3")

# keep alias for plots that reference the UE models
model_visits = model_visits_ue
model_enroll = model_enroll_ue

coef_table(model_visits_ue,     "MODEL A: Direct Visits + Unemployment Rate")
coef_table(model_enroll_ue,     "MODEL B: Direct Enrollments + Unemployment Rate")
coef_table(model_visits_lag_ue, "MODEL C: Direct Visits (lags) + Unemployment Rate")
coef_table(model_enroll_lag_ue, "MODEL D: Direct Enrollments (lags) + Unemployment Rate")

# ---------------------------------------------------------------------------
# MODELS WITHOUT UNEMPLOYMENT RATE  (clean dataset)
# ---------------------------------------------------------------------------
Xv_no  = sm.add_constant(df_m[FEATURES_NO_UE])
Xe_no  = sm.add_constant(df_m[FEATURES_NO_UE])
Xvl_no = sm.add_constant(df_m[LAG_FEATURES_NO_UE])
Xel_no = sm.add_constant(df_m[LAG_FEATURES_NO_UE])

model_visits_no      = sm.OLS(Yv, Xv_no).fit(cov_type="HC3")
model_enroll_no      = sm.OLS(Ye, Xe_no).fit(cov_type="HC3")
model_visits_lag_no  = sm.OLS(Yv, Xvl_no).fit(cov_type="HC3")
model_enroll_lag_no  = sm.OLS(Ye, Xel_no).fit(cov_type="HC3")

coef_table(model_visits_no,     "MODEL E: Direct Visits (no UE rate, clean data)")
coef_table(model_enroll_no,     "MODEL F: Direct Enrollments (no UE rate, clean data)")
coef_table(model_visits_lag_no, "MODEL G: Direct Visits (lags, no UE rate, clean data)")
coef_table(model_enroll_lag_no, "MODEL H: Direct Enrollments (lags, no UE rate, clean data)")

# ---------------------------------------------------------------------------
# VIF
# ---------------------------------------------------------------------------
print("\n\n--- VIF: Model A (with UE) ---")
vif_ue = pd.DataFrame({
    "Variable": Xv_ue.columns,
    "VIF": [variance_inflation_factor(Xv_ue.values, i) for i in range(Xv_ue.shape[1])]
})
print(vif_ue.round(2).to_string(index=False))

print("\n--- VIF: Model E (no UE) ---")
vif_no = pd.DataFrame({
    "Variable": Xv_no.columns,
    "VIF": [variance_inflation_factor(Xv_no.values, i) for i in range(Xv_no.shape[1])]
})
print(vif_no.round(2).to_string(index=False))

# ---------------------------------------------------------------------------
# MODEL COMPARISON TABLE
# ---------------------------------------------------------------------------
print("\n\n--- MODEL COMPARISON ---")
header = f"{'Model':<10} {'Dep Var':<22} {'UE Rate':>7} {'R²':>7} {'Adj-R²':>8} {'AI p-val':>10} {'AI coef':>9}  DW"
print(header)
print("-" * len(header))
rows_cmp = [
    ("A", "Direct Visits",       "Yes", model_visits_ue),
    ("B", "Direct Enrollments",  "Yes", model_enroll_ue),
    ("C", "Visits (lags)",       "Yes", model_visits_lag_ue),
    ("D", "Enrollments (lags)",  "Yes", model_enroll_lag_ue),
    ("E", "Direct Visits",       "No",  model_visits_no),
    ("F", "Direct Enrollments",  "No",  model_enroll_no),
    ("G", "Visits (lags)",       "No",  model_visits_lag_no),
    ("H", "Enrollments (lags)",  "No",  model_enroll_lag_no),
]
ai_key = {"A":"ai_visibility","B":"ai_visibility","C":"ai_vis_lag1","D":"ai_vis_lag1",
          "E":"ai_visibility","F":"ai_visibility","G":"ai_vis_lag1","H":"ai_vis_lag1"}
for mid, dep, ue, m in rows_cmp:
    ak = ai_key[mid]
    sig = "***" if m.pvalues[ak]<0.001 else "**" if m.pvalues[ak]<0.01 else "*" if m.pvalues[ak]<0.05 else "." if m.pvalues[ak]<0.1 else ""
    print(f"{mid:<10} {dep:<22} {ue:>7} {m.rsquared:>7.3f} {m.rsquared_adj:>8.3f} "
          f"{m.pvalues[ak]:>10.4f} {m.params[ak]:>9.2f}{sig:>3}  {durbin_watson(m.resid):.2f}")

# ---------------------------------------------------------------------------
# ECONOMIC INTERPRETATION
# ---------------------------------------------------------------------------
print("\n\n--- ECONOMIC INTERPRETATION ---")
ai_mean  = df_m["ai_visibility"].mean()
vis_mean = df_m["direct_visits"].mean()
enr_mean = df_m["direct_enrollments"].mean()

for label, m_ue, m_no, ymean in [
    ("Direct Visits",      model_visits_ue, model_visits_no, vis_mean),
    ("Direct Enrollments", model_enroll_ue, model_enroll_no, enr_mean),
]:
    print(f"\n{label}  (mean={ymean:,.0f})")
    for tag, m in [("with UE", m_ue), ("no UE ", m_no)]:
        c   = m.params["ai_visibility"]
        p   = m.pvalues["ai_visibility"]
        el  = c * (ai_mean / ymean)
        sig = "***" if p<0.001 else "**" if p<0.01 else "*" if p<0.05 else "." if p<0.1 else "ns"
        print(f"  [{tag}]  AI +1pt → {c:+.1f}  (p={p:.4f} {sig})  elasticity={el:.3f}")


# ---------------------------------------------------------------------------
# CSV EXPORTS
# ---------------------------------------------------------------------------

# 1. Clean modelling dataset with fitted values & residuals for all 8 models
df_out = df_m[["date", "ai_visibility", "direct_visits", "direct_enrollments",
               "brand_spend_k", "nb_spend_k", "unemployment_rate",
               "is_weekend", "day_of_week", "month"]].copy()

df_out["fitted_visits_with_ue"]      = model_visits_ue.fittedvalues.values
df_out["resid_visits_with_ue"]       = model_visits_ue.resid.values
df_out["fitted_enroll_with_ue"]      = model_enroll_ue.fittedvalues.values
df_out["resid_enroll_with_ue"]       = model_enroll_ue.resid.values
df_out["fitted_visits_no_ue"]        = model_visits_no.fittedvalues.values
df_out["resid_visits_no_ue"]         = model_visits_no.resid.values
df_out["fitted_enroll_no_ue"]        = model_enroll_no.fittedvalues.values
df_out["resid_enroll_no_ue"]         = model_enroll_no.resid.values

data_csv = os.path.join(OUTPUT_DIR, "regression_data.csv")
df_out.round(4).to_csv(data_csv, index=False)
print(f"\nClean data + fitted values → {data_csv}")

# 2. Coefficient results for all 8 models
coef_rows = []
for mid, dep, ue_flag, m in rows_cmp:
    ci = m.conf_int()
    ci.columns = ["ci_lower", "ci_upper"]
    for var in m.params.index:
        sig = "***" if m.pvalues[var]<0.001 else "**" if m.pvalues[var]<0.01 \
              else "*" if m.pvalues[var]<0.05 else "." if m.pvalues[var]<0.1 else ""
        coef_rows.append({
            "model":         mid,
            "dependent_var": dep,
            "ue_rate_included": ue_flag,
            "variable":      var,
            "coefficient":   round(m.params[var], 4),
            "std_err":        round(m.bse[var], 4),
            "t_stat":         round(m.tvalues[var], 4),
            "p_value":        round(m.pvalues[var], 4),
            "ci_lower_95":    round(ci.loc[var, "ci_lower"], 4),
            "ci_upper_95":    round(ci.loc[var, "ci_upper"], 4),
            "significance":   sig,
            "r_squared":      round(m.rsquared, 4),
            "adj_r_squared":  round(m.rsquared_adj, 4),
            "n_obs":          int(m.nobs),
            "durbin_watson":  round(durbin_watson(m.resid), 4),
        })

coef_df = pd.DataFrame(coef_rows)
coef_csv = os.path.join(OUTPUT_DIR, "regression_coefficients.csv")
coef_df.to_csv(coef_csv, index=False)
print(f"Coefficient results (all 8 models) → {coef_csv}")

# 3. Outlier log
outlier_csv = os.path.join(OUTPUT_DIR, "outliers_removed.csv")
outliers.to_csv(outlier_csv, index=False)
print(f"Outlier log → {outlier_csv}")

# ---------------------------------------------------------------------------
# PLOTS
# ---------------------------------------------------------------------------
plt.rcParams.update({"figure.dpi": 150, "font.size": 9})
sns.set_style("whitegrid")

fig, axes = plt.subplots(3, 3, figsize=(17, 14))
fig.suptitle(
    "Chime AI Visibility → Direct Visits & Enrollments\n"
    "Multivariate Regression  |  Outliers removed (IQR)  |  + Unemployment Rate",
    fontsize=12, fontweight="bold"
)

# Row 0 ─ time series
ax = axes[0, 0]
ax.plot(df_clean["date"], df_clean["ai_visibility"], color="#1f77b4", lw=1.2)
ax.set_title("AI Visibility Score")
ax.set_ylabel("Score (%)")
ax.tick_params(axis="x", rotation=30)

ax = axes[0, 1]
ax.plot(df_clean["date"], df_clean["direct_visits"] / 1000, color="#ff7f0e", lw=1.2)
ax.set_title("Daily Direct Visits (clean)")
ax.set_ylabel("Visits (000s)")
ax.tick_params(axis="x", rotation=30)

ax = axes[0, 2]
ax2 = ax.twinx()
ax.plot(df_clean["date"], df_clean["ai_visibility"], color="#1f77b4", lw=1.2, label="AI Vis")
ax2.plot(df_clean["date"], df_clean["unemployment_rate"], color="#d62728", lw=1.2,
         linestyle="--", label="Unemployment %")
ax.set_title("AI Visibility vs Unemployment Rate")
ax.set_ylabel("AI Visibility (%)", color="#1f77b4")
ax2.set_ylabel("Unemployment Rate (%)", color="#d62728")
ax.tick_params(axis="x", rotation=30)
lines1, l1 = ax.get_legend_handles_labels()
lines2, l2 = ax2.get_legend_handles_labels()
ax.legend(lines1 + lines2, l1 + l2, fontsize=7, loc="upper right")

# Row 1 ─ scatter + coef plots
ax = axes[1, 0]
sc = ax.scatter(df_m["ai_visibility"], df_m["direct_enrollments"],
                c=df_m["unemployment_rate"], cmap="RdYlGn_r", alpha=0.6, s=20)
z = np.polyfit(df_m["ai_visibility"], df_m["direct_enrollments"], 1)
x_line = np.linspace(df_m["ai_visibility"].min(), df_m["ai_visibility"].max(), 100)
ax.plot(x_line, np.poly1d(z)(x_line), "b--", lw=1.5,
        label=f"r={np.corrcoef(df_m['ai_visibility'], df_m['direct_enrollments'])[0,1]:.2f}")
plt.colorbar(sc, ax=ax, label="Unemp. Rate %")
ax.set_title("AI Visibility vs Direct Enrollments\n(color = unemployment rate)")
ax.set_xlabel("AI Visibility Score")
ax.set_ylabel("Direct Enrollments")
ax.legend(fontsize=8)

ax = axes[1, 1]
vars_b = ["ai_visibility", "brand_spend_k", "nb_spend_k", "unemployment_rate", "is_weekend"]
labels_b = ["AI Visibility", "Brand Spend $K", "NB Spend $K", "Unemployment %", "Weekend"]
coefs_b  = [model_enroll.params[v] for v in vars_b]
errors_b = [model_enroll.bse[v]   for v in vars_b]
colors_b = ["#2ca02c" if c > 0 else "#d62728" for c in coefs_b]
y_pos = range(len(vars_b))
ax.barh(y_pos, coefs_b, xerr=errors_b, color=colors_b, alpha=0.75, height=0.5)
ax.set_yticks(y_pos)
ax.set_yticklabels(labels_b)
ax.axvline(0, color="black", lw=0.8)
ax.set_title(f"Model B Coefficients\nDirect Enrollments (R²={model_enroll.rsquared:.2f})")
ax.set_xlabel("Coefficient ± SE")

ax = axes[1, 2]
vars_a = ["ai_visibility", "brand_spend_k", "nb_spend_k", "unemployment_rate", "is_weekend"]
coefs_a  = [model_visits.params[v] for v in vars_a]
errors_a = [model_visits.bse[v]   for v in vars_a]
colors_a = ["#2ca02c" if c > 0 else "#d62728" for c in coefs_a]
ax.barh(y_pos, coefs_a, xerr=errors_a, color=colors_a, alpha=0.75, height=0.5)
ax.set_yticks(y_pos)
ax.set_yticklabels(labels_b)
ax.axvline(0, color="black", lw=0.8)
ax.set_title(f"Model A Coefficients\nDirect Visits (R²={model_visits.rsquared:.2f})")
ax.set_xlabel("Coefficient ± SE")

# Row 2 ─ actual vs fitted + residuals + unemployment vs enrollments
ax = axes[2, 0]
ax.scatter(model_enroll.fittedvalues, Ye, alpha=0.4, s=15, color="#2ca02c")
mn = min(model_enroll.fittedvalues.min(), Ye.min())
mx = max(model_enroll.fittedvalues.max(), Ye.max())
ax.plot([mn, mx], [mn, mx], "r--", lw=1.2)
ax.set_title(f"Actual vs Fitted – Enrollments\n(R²={model_enroll.rsquared:.2f})")
ax.set_xlabel("Fitted"); ax.set_ylabel("Actual")

ax = axes[2, 1]
resid = model_enroll.resid
ax.scatter(df_m["date"], resid, alpha=0.4, s=15, color="#9467bd")
ax.axhline(0, color="black", lw=0.8)
ax.set_title("Residuals Over Time (Model B)")
ax.set_ylabel("Residual")
ax.tick_params(axis="x", rotation=30)

ax = axes[2, 2]
sc2 = ax.scatter(df_m["unemployment_rate"], df_m["direct_enrollments"],
                 c=df_m["ai_visibility"], cmap="Blues", alpha=0.6, s=20)
plt.colorbar(sc2, ax=ax, label="AI Visibility Score")
z2 = np.polyfit(df_m["unemployment_rate"], df_m["direct_enrollments"], 1)
x2 = np.linspace(df_m["unemployment_rate"].min(), df_m["unemployment_rate"].max(), 100)
ax.plot(x2, np.poly1d(z2)(x2), "r--", lw=1.5,
        label=f"r={np.corrcoef(df_m['unemployment_rate'], df_m['direct_enrollments'])[0,1]:.2f}")
ax.set_title("Unemployment Rate vs Direct Enrollments\n(color = AI Visibility)")
ax.set_xlabel("Unemployment Rate (%)"); ax.set_ylabel("Direct Enrollments")
ax.legend(fontsize=8)

plt.tight_layout()
plot_path = os.path.join(OUTPUT_DIR, "regression_results.png")
plt.savefig(plot_path, bbox_inches="tight")
print(f"\n\nPlot saved → {plot_path}")

# Save text summaries
summary_path = os.path.join(OUTPUT_DIR, "regression_summary.txt")
with open(summary_path, "w") as f:
    for m, t in [
        (model_visits_ue,     "MODEL A: Direct Visits + UE Rate"),
        (model_enroll_ue,     "MODEL B: Direct Enrollments + UE Rate"),
        (model_visits_lag_ue, "MODEL C: Direct Visits (lags) + UE Rate"),
        (model_enroll_lag_ue, "MODEL D: Direct Enrollments (lags) + UE Rate"),
        (model_visits_no,     "MODEL E: Direct Visits (no UE Rate)"),
        (model_enroll_no,     "MODEL F: Direct Enrollments (no UE Rate)"),
        (model_visits_lag_no, "MODEL G: Direct Visits (lags, no UE Rate)"),
        (model_enroll_lag_no, "MODEL H: Direct Enrollments (lags, no UE Rate)"),
    ]:
        f.write(f"\n{'='*70}\n{t}\n{'='*70}\n")
        f.write(m.summary().as_text())
        f.write("\n")
print(f"Full summaries saved → {summary_path}")
