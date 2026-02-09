# 🐦 ScoutAgent Simulation Data Guide

**Last Updated:** November 17, 2025
**Purpose:** Guide for creating realistic Twitter/X flood report simulation data

---

## 📋 Overview

ScoutAgent scrapes Twitter/X for crowdsourced flood reports. In **simulation mode**, it loads synthetic tweets from JSON files instead of scraping live data.

### **Existing Files** (Already Created)

```
masfro-backend/app/data/synthetic/
├── scout_scenario_1_typhoon_scenario_-_heavy_flooding.json    ✅ (100 tweets)
├── scout_scenario_2_monsoon_rain_-_moderate_flooding.json     ✅ (50 tweets)
├── scout_scenario_3_light_rain_-_minimal_impact.json          ✅ (30 tweets)
└── scout_data_summary.json                                     ✅ (Metadata)
```

---

## 📊 Data Structure

Each scenario file contains:

1. **Metadata** - Scenario description
2. **Tweets Array** - Simulated Twitter/X posts
3. **Ground Truth** - Actual flood severity (for testing)

---

## 📄 ScoutAgent Data Format

### **Complete Example**

```json
{
  "scenario_name": "Heavy Flooding - Typhoon Scenario",
  "scenario_id": 1,
  "description": "Severe typhoon causing widespread flooding across Marikina City",
  "start_time": "2025-11-13T08:00:00",
  "duration_hours": 3,
  "total_tweets": 100,
  "flood_related_tweets": 78,

  "tweets": [
    {
      "tweet_id": "2584053931600684150",
      "username": "marikina_news",
      "display_name": "Marikina News Network",
      "verified": true,
      "text": "⚠️ BAHA SA NANGKA! Knee-deep ang tubig sa JP Rizal Avenue. Hindi madaan ang mga sasakyan.避難してください! #MarikinFloods #BahaNangka",
      "timestamp": "2025-11-13T08:15:00Z",
      "url": "https://x.com/marikina_news/status/2584053931600684150",
      "replies": "23",
      "retweets": "145",
      "likes": "289",
      "media_urls": [
        "https://pbs.twimg.com/media/fake_image_1.jpg"
      ],
      "hashtags": [
        "#MarikinFloods",
        "#BahaNangka",
        "#MarikinaAlert"
      ],
      "mentions": [
        "@marikinalgu",
        "@MMDA"
      ],
      "scraped_at": "2025-11-13T08:16:34",

      "_ground_truth": {
        "location": "Nangka",
        "coordinates": {
          "lat": 14.6507,
          "lon": 121.1009
        },
        "severity_level": "moderate",
        "severity_score": 0.6,
        "flood_depth_cm": 50,
        "passability": "impassable",
        "is_flood_related": true,
        "confidence": 0.9,
        "language": "tagalog",
        "keywords_matched": [
          "baha",
          "knee-deep",
          "hindi madaan"
        ]
      }
    },

    {
      "tweet_id": "4138805422888495196",
      "username": "marikina_resident",
      "display_name": "Juan Dela Cruz",
      "verified": false,
      "text": "Waist level na ang baha sa Malanday! Please send help! Trapped kami sa bahay. 🆘 #MarikinFloods #Malanday",
      "timestamp": "2025-11-13T08:20:00Z",
      "url": "https://x.com/marikina_resident/status/4138805422888495196",
      "replies": "15",
      "retweets": "67",
      "likes": "103",
      "media_urls": [],
      "hashtags": [
        "#MarikinFloods",
        "#Malanday"
      ],
      "mentions": [],
      "scraped_at": "2025-11-13T08:21:11",

      "_ground_truth": {
        "location": "Malanday",
        "coordinates": {
          "lat": 14.6561,
          "lon": 121.0889
        },
        "severity_level": "severe",
        "severity_score": 0.8,
        "flood_depth_cm": 90,
        "passability": "impassable",
        "is_flood_related": true,
        "confidence": 0.95,
        "language": "tagalog",
        "keywords_matched": [
          "waist level",
          "baha",
          "trapped"
        ]
      }
    },

    {
      "tweet_id": "5924869806717412746",
      "username": "weather_ph",
      "display_name": "Weather Philippines",
      "verified": true,
      "text": "UPDATE: Heavy rainfall continues in Marikina area. River levels rising rapidly at Sto. Niño station (18.5m). Residents near Marikina River advised to evacuate immediately. #WeatherAlert #MarikinFloods",
      "timestamp": "2025-11-13T08:25:00Z",
      "url": "https://x.com/weather_ph/status/5924869806717412746",
      "replies": "89",
      "retweets": "234",
      "likes": "412",
      "media_urls": [
        "https://pbs.twimg.com/media/fake_radar_image.jpg"
      ],
      "hashtags": [
        "#WeatherAlert",
        "#MarikinFloods"
      ],
      "mentions": [
        "@PAGASA_DOST"
      ],
      "scraped_at": "2025-11-13T08:26:05",

      "_ground_truth": {
        "location": "Sto. Niño",
        "coordinates": {
          "lat": 14.6553,
          "lon": 121.0967
        },
        "severity_level": "critical",
        "severity_score": 1.0,
        "flood_depth_cm": 150,
        "passability": "impassable",
        "is_flood_related": true,
        "confidence": 1.0,
        "language": "english",
        "keywords_matched": [
          "heavy rainfall",
          "river levels rising",
          "evacuate"
        ]
      }
    },

    {
      "tweet_id": "7821035832267902453",
      "username": "sm_marikina_official",
      "display_name": "SM City Marikina",
      "verified": true,
      "text": "MALL OPERATIONS UPDATE: Due to heavy rain, parking areas are experiencing ankle-deep flooding. Shoppers are advised to park on upper levels. Mall remains OPEN. #SMMarikina",
      "timestamp": "2025-11-13T08:30:00Z",
      "url": "https://x.com/sm_marikina_official/status/7821035832267902453",
      "replies": "12",
      "retweets": "34",
      "likes": "78",
      "media_urls": [],
      "hashtags": [
        "#SMMarikina"
      ],
      "mentions": [],
      "scraped_at": "2025-11-13T08:31:20",

      "_ground_truth": {
        "location": "SM Marikina",
        "coordinates": {
          "lat": 14.6394,
          "lon": 121.1067
        },
        "severity_level": "minor",
        "severity_score": 0.3,
        "flood_depth_cm": 15,
        "passability": "passable_with_caution",
        "is_flood_related": true,
        "confidence": 0.8,
        "language": "english",
        "keywords_matched": [
          "ankle-deep flooding",
          "heavy rain"
        ]
      }
    },

    {
      "tweet_id": "9123456789012345678",
      "username": "marikina_lgu",
      "display_name": "Marikina LGU Official",
      "verified": true,
      "text": "ROAD CLOSURE: JP Rizal Avenue (Nangka to Concepcion section) is now CLOSED to all vehicles due to severe flooding. Use alternate routes via Marcos Highway. #MarikinTraffic #MarikinFloods",
      "timestamp": "2025-11-13T08:35:00Z",
      "url": "https://x.com/marikina_lgu/status/9123456789012345678",
      "replies": "56",
      "retweets": "189",
      "likes": "245",
      "media_urls": [],
      "hashtags": [
        "#MarikinTraffic",
        "#MarikinFloods"
      ],
      "mentions": [
        "@MMDA",
        "@marikina_news"
      ],
      "scraped_at": "2025-11-13T08:36:15",

      "_ground_truth": {
        "location": "JP Rizal Avenue",
        "coordinates": {
          "lat": 14.6489,
          "lon": 121.0956
        },
        "severity_level": "severe",
        "severity_score": 0.85,
        "flood_depth_cm": 80,
        "passability": "closed",
        "is_flood_related": true,
        "confidence": 1.0,
        "language": "english",
        "keywords_matched": [
          "road closure",
          "severe flooding",
          "closed to all vehicles"
        ]
      }
    },

    {
      "tweet_id": "1029384756102938475",
      "username": "traffic_update_ph",
      "display_name": "Metro Manila Traffic",
      "verified": false,
      "text": "Traffic buildup on Marcos Highway due to flooding on JP Rizal. Travel time from QC to Marikina now 2+ hours. Avoid the area if possible. #MarikinaTraffic",
      "timestamp": "2025-11-13T08:40:00Z",
      "url": "https://x.com/traffic_update_ph/status/1029384756102938475",
      "replies": "8",
      "retweets": "23",
      "likes": "45",
      "media_urls": [],
      "hashtags": [
        "#MarikinaTraffic"
      ],
      "mentions": [],
      "scraped_at": "2025-11-13T08:41:05",

      "_ground_truth": {
        "location": "Marcos Highway",
        "coordinates": {
          "lat": 14.6631,
          "lon": 121.0822
        },
        "severity_level": "traffic_only",
        "severity_score": 0.2,
        "flood_depth_cm": 0,
        "passability": "slow_traffic",
        "is_flood_related": false,
        "confidence": 0.6,
        "language": "english",
        "keywords_matched": [
          "traffic",
          "flooding"
        ]
      }
    },

    {
      "tweet_id": "5647382910564738291",
      "username": "abs_cbn_news",
      "display_name": "ABS-CBN News",
      "verified": true,
      "text": "LIVE: Marikina residents evacuating as river level reaches critical 18.5 meters. Evacuation centers now open at Marikina Sports Center and schools. Updates to follow. 📺 #ABSCBNNews #MarikinFloods",
      "timestamp": "2025-11-13T08:45:00Z",
      "url": "https://x.com/abs_cbn_news/status/5647382910564738291",
      "replies": "134",
      "retweets": "456",
      "likes": "892",
      "media_urls": [
        "https://pbs.twimg.com/media/fake_evacuation_photo.jpg"
      ],
      "hashtags": [
        "#ABSCBNNews",
        "#MarikinFloods"
      ],
      "mentions": [
        "@marikinalgu"
      ],
      "scraped_at": "2025-11-13T08:46:22",

      "_ground_truth": {
        "location": "Marikina Sports Center",
        "coordinates": {
          "lat": 14.6380,
          "lon": 121.0997
        },
        "severity_level": "evacuation",
        "severity_score": 0.95,
        "flood_depth_cm": 120,
        "passability": "evacuation_required",
        "is_flood_related": true,
        "confidence": 1.0,
        "language": "english",
        "keywords_matched": [
          "evacuating",
          "critical",
          "evacuation centers"
        ]
      }
    }
  ]
}
```

---

## 🎯 Severity Levels Guide

### **Depth-Based Classification**

| Severity Level | Depth (cm) | Description | Risk Score | Filipino Terms |
|----------------|-----------|-------------|------------|----------------|
| `none` | 0 | No flooding | 0.0 | "Walang baha" |
| `rain_only` | 0 | Rain but no standing water | 0.0 | "Ulan lang" |
| `minor` | 1-20 | Ankle-deep | 0.1-0.3 | "Sakong level" |
| `moderate` | 21-60 | Knee-deep | 0.4-0.6 | "Tuhod level" |
| `severe` | 61-100 | Waist-deep | 0.7-0.9 | "Baywang level" |
| `critical` | 101+ | Above waist, dangerous | 0.9-1.0 | "Dibdib level", "Liig level" |
| `evacuation` | N/A | Mandatory evacuation | 1.0 | "Lumikas na" |

---

## 📍 Location Coverage

### **Barangays** (16 total)

```json
{
  "barangays": [
    {"name": "Nangka", "lat": 14.6507, "lon": 121.1009},
    {"name": "Malanday", "lat": 14.6561, "lon": 121.0889},
    {"name": "Sto. Niño", "lat": 14.6553, "lon": 121.0967},
    {"name": "Parang", "lat": 14.6700, "lon": 121.0911},
    {"name": "Tumana", "lat": 14.6789, "lon": 121.1100},
    {"name": "Concepcion Uno", "lat": 14.6664, "lon": 121.1067},
    {"name": "Concepcion Dos", "lat": 14.6708, "lon": 121.1156},
    {"name": "Barangka", "lat": 14.6386, "lon": 121.0978},
    {"name": "Sta. Elena", "lat": 14.6489, "lon": 121.0956},
    {"name": "Marikina Heights", "lat": 14.6631, "lon": 121.0822},
    {"name": "Fortune", "lat": 14.6689, "lon": 121.0956},
    {"name": "Industrial Valley", "lat": 14.6520, "lon": 121.0870},
    {"name": "Jesus Dela Peña", "lat": 14.6394, "lon": 121.0856},
    {"name": "Kalumpang", "lat": 14.6394, "lon": 121.1067},
    {"name": "San Roque", "lat": 14.6319, "lon": 121.1156},
    {"name": "Tañong", "lat": 14.6425, "lon": 121.0892}
  ]
}
```

### **Major Landmarks**

```json
{
  "landmarks": [
    {"name": "SM Marikina", "lat": 14.6394, "lon": 121.1067},
    {"name": "Marikina Sports Center", "lat": 14.6380, "lon": 121.0997},
    {"name": "Riverbanks Center", "lat": 14.6394, "lon": 121.1067},
    {"name": "Marikina City Hall", "lat": 14.6489, "lon": 121.0956},
    {"name": "Robinsons Metro East", "lat": 14.6319, "lon": 121.1156},
    {"name": "LRT-2 Santolan Station", "lat": 14.6306, "lon": 121.0850},
    {"name": "LRT-2 Katipunan Station", "lat": 14.6331, "lon": 121.0728}
  ]
}
```

### **Major Roads**

```json
{
  "roads": [
    {"name": "JP Rizal Avenue", "lat": 14.6489, "lon": 121.0956},
    {"name": "Marcos Highway", "lat": 14.6631, "lon": 121.0822},
    {"name": "Shoe Avenue", "lat": 14.6553, "lon": 121.0967},
    {"name": "Sumulong Highway", "lat": 14.6400, "lon": 121.1000},
    {"name": "Gil Fernando Avenue", "lat": 14.6631, "lon": 121.0822},
    {"name": "A. Bonifacio Avenue", "lat": 14.6536, "lon": 121.1032}
  ]
}
```

---

## 🗣️ Language & Keywords

### **Filipino/Tagalog Flood Terms**

```json
{
  "flood_keywords": [
    "baha",
    "bumaha",
    "bahain",
    "pagbaha",
    "binaha",
    "apaw",
    "umapaw",
    "pisan",
    "dilubyo"
  ],

  "depth_indicators": {
    "minor": ["sakong level", "ankle-deep", "mababaw"],
    "moderate": ["tuhod level", "knee-deep", "katamtaman"],
    "severe": ["baywang level", "waist-deep", "mataas"],
    "critical": ["dibdib level", "liig level", "gulu-gulo", "chest-deep"]
  },

  "passability": {
    "clear": ["walang baha", "okay", "madaan", "safe", "tuyo", "humupa", "keri pa"],
    "blocked": ["sarado", "hindi madaan", "barado", "naipit", "trapped", "stuck"],
    "slow": ["traffic", "mabagal", "slow", "congestion"]
  },

  "urgency": {
    "warning": ["ingat", "mag-ingat", "be careful", "bantayan"],
    "evacuation": ["lumikas", "evacuate", "umalis", "leave now", "tumakas"]
  }
}
```

---

## 📝 Tweet Composition Guidelines

### **Realistic Tweet Patterns**

1. **News Reports** (High confidence: 0.9-1.0)
   ```
   "⚠️ BAHA SA [LOCATION]! [DEPTH] ang tubig. [STATUS]. #MarikinaFloods"
   ```

2. **Personal Reports** (Medium confidence: 0.6-0.8)
   ```
   "[DEPTH] na ang baha sa [LOCATION]! [EMOTIONAL_REACTION] #MarikinFloods"
   ```

3. **Traffic Updates** (Low flood relevance: 0.3-0.5)
   ```
   "Traffic buildup on [ROAD] due to flooding. [TRAVEL_TIME]. #MarikinaTraffic"
   ```

4. **Official Announcements** (Very high confidence: 1.0)
   ```
   "ROAD CLOSURE: [ROAD] is now CLOSED due to [SEVERITY] flooding. [INSTRUCTIONS]."
   ```

5. **Evacuation Alerts** (Critical: 1.0)
   ```
   "EVACUATE NOW: [LOCATION] residents advised to evacuate to [EVACUATION_CENTER]."
   ```

---

## 🎨 Adding Realism

### **Hashtags Distribution**

```json
{
  "common_hashtags": [
    "#MarikinFloods",
    "#BahaSaMarikina",
    "#MarikinaAlert",
    "#MarikinaTraffic",
    "#WeatherAlert",
    "#PhFloods",
    "#WalangPasok"
  ],

  "barangay_hashtags": [
    "#BahaNangka",
    "#MalandayFloods",
    "#StoNinoAlert"
  ],

  "media_hashtags": [
    "#ABSCBNNews",
    "#GMANews",
    "#CNN_Philippines"
  ]
}
```

### **Username Patterns**

```json
{
  "official_accounts": [
    "marikina_lgu",
    "PAGASA_DOST",
    "MMDA",
    "abs_cbn_news",
    "gma_news",
    "weather_ph"
  ],

  "local_accounts": [
    "marikina_news",
    "marikina_resident",
    "marikina_updates",
    "sm_marikina_official"
  ],

  "citizen_patterns": [
    "user_[barangay]",
    "[firstname]_marikina",
    "resident_[number]"
  ]
}
```

---

## 🔄 How ScoutAgent Uses This Data

### **Loading Process**

```python
scout_agent = ScoutAgent(
    agent_id="scout_001",
    simulation_mode=True,
    simulation_scenario=1  # Loads scenario 1 JSON
)

# Internally loads:
# app/data/synthetic/scout_scenario_1_typhoon_scenario_-_heavy_flooding.json
```

### **Tweet Processing**

1. **Extract Location**
   ```python
   nlp_processor.extract_flood_info(tweet["text"])
   # Returns: {"locations": ["Nangka"], "severity": 0.6}
   ```

2. **Geocode Location**
   ```python
   geocoder.get_coordinates("Nangka")
   # Returns: (14.6507, 121.1009)
   ```

3. **Create Scout Report**
   ```python
   {
       "location": "Nangka",
       "coordinates": {"lat": 14.6507, "lon": 121.1009},
       "severity": 0.6,
       "confidence": 0.7,
       "source": "twitter"
   }
   ```

4. **Forward to HazardAgent**
   ```python
   hazard_agent.process_scout_data_with_coordinates([report])
   ```

---

## ✅ Validation Rules

Before using scout simulation data:

- [ ] Each tweet has unique `tweet_id`
- [ ] Timestamps follow chronological order
- [ ] Location names match LocationGeocoder database
- [ ] Coordinates are within Marikina bounds (14.60-14.70 lat, 121.05-121.13 lon)
- [ ] Severity scores align with depth/description (0.0-1.0)
- [ ] `is_flood_related` matches content analysis
- [ ] Ground truth confidence is realistic (0.6-1.0)
- [ ] Language field matches text content
- [ ] Keywords matched list is accurate

---

## 📊 Recommended Distribution

### **Scenario 1: Heavy Flooding** (100 tweets)
- 78 flood-related (78%)
- 22 non-flood (22%)

**Severity Breakdown:**
- Critical: 15 tweets (15%)
- Severe: 25 tweets (25%)
- Moderate: 20 tweets (20%)
- Minor: 10 tweets (10%)
- Rain only: 8 tweets (8%)
- Traffic/other: 22 tweets (22%)

### **Scenario 2: Moderate Flooding** (50 tweets)
- 40 flood-related (80%)
- 10 non-flood (20%)

**Severity Breakdown:**
- Critical: 5 tweets (10%)
- Severe: 10 tweets (20%)
- Moderate: 15 tweets (30%)
- Minor: 10 tweets (20%)
- Rain only: 10 tweets (20%)

### **Scenario 3: Light Flooding** (30 tweets)
- 24 flood-related (80%)
- 6 non-flood (20%)

**Severity Breakdown:**
- Critical: 0 tweets (0%)
- Severe: 2 tweets (7%)
- Moderate: 8 tweets (27%)
- Minor: 14 tweets (47%)
- Rain only: 6 tweets (20%)

---

## 🎯 Summary

**ScoutAgent simulation data provides:**
1. Realistic Twitter/X flood reports
2. Geographic coverage (16 barangays, 50+ landmarks)
3. Mixed Filipino-English content
4. Ground truth for validation
5. Temporal progression (chronological tweets)

**Next:** See `COMPLETE_SIMULATION_WORKFLOW.md` for integration guide

---

**Files Generated:**
- ✅ `scout_scenario_1_typhoon_scenario_-_heavy_flooding.json`
- ✅ `scout_scenario_2_monsoon_rain_-_moderate_flooding.json`
- ✅ `scout_scenario_3_light_rain_-_minimal_impact.json`
- ✅ `scout_data_summary.json`

These files are already created and ready to use!
