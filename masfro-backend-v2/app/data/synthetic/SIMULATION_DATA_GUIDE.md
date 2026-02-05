# 🎮 Simulation Data Guide for MAS-FRO

**Last Updated:** November 17, 2025
**Purpose:** Complete guide for creating simulation data for FloodAgent and ScoutAgent

---

## 📋 Overview

This guide shows you how to create **realistic simulation data** for testing the MAS-FRO system without requiring real-time API access to PAGASA, OpenWeatherMap, or Twitter/X.

### **What You'll Create**

1. **FloodAgent Simulation Data** (3 JSON files)
   - River levels from PAGASA stations
   - Weather data (rainfall, temperature, wind)
   - Dam water levels

2. **ScoutAgent Simulation Data** (Already exists, customizable)
   - Twitter/X flood reports
   - Location-based severity reports

---

## 🌊 FloodAgent Simulation Data

### **Required Files**

```
masfro-backend/app/data/synthetic/
├── flood_simulation_scenario_1.json    # Heavy flooding (Typhoon)
├── flood_simulation_scenario_2.json    # Moderate flooding (Monsoon)
└── flood_simulation_scenario_3.json    # Light flooding (Normal rain)
```

### **Data Structure Overview**

FloodAgent collects 3 types of data:
1. **River Levels** (17 PAGASA stations)
2. **Weather Data** (OpenWeatherMap format)
3. **Dam Levels** (3 major dams)

---

## 📄 Template: flood_simulation_scenario_1.json

**Scenario:** Heavy Flooding - Typhoon Conditions

```json
{
  "scenario_name": "Heavy Flooding - Typhoon Scenario",
  "scenario_id": 1,
  "description": "Severe typhoon with torrential rain, high river levels, and dam releases",
  "start_time": "2025-11-13T08:00:00",
  "duration_hours": 12,
  "severity": "critical",

  "river_levels": {
    "metadata": {
      "source": "PAGASA River Level Monitoring",
      "stations_total": 17,
      "last_update": "2025-11-13T10:00:00"
    },
    "stations": [
      {
        "station_name": "Sto Nino",
        "location": "Marikina River - Sto. Niño Bridge",
        "coordinates": {
          "lat": 14.6553,
          "lon": 121.0967
        },
        "water_level_m": 18.5,
        "normal_level_m": 12.0,
        "alert_level_m": 15.0,
        "alarm_level_m": 16.0,
        "critical_level_m": 18.0,
        "status": "critical",
        "status_code": 3,
        "risk_score": 1.0,
        "trend": "rising",
        "change_rate_m_per_hour": 0.5,
        "timestamp": "2025-11-13T10:00:00"
      },
      {
        "station_name": "Nangka",
        "location": "Marikina River - Nangka",
        "coordinates": {
          "lat": 14.6507,
          "lon": 121.1009
        },
        "water_level_m": 17.8,
        "normal_level_m": 11.5,
        "alert_level_m": 14.5,
        "alarm_level_m": 15.5,
        "critical_level_m": 17.5,
        "status": "critical",
        "status_code": 3,
        "risk_score": 1.0,
        "trend": "rising",
        "change_rate_m_per_hour": 0.6,
        "timestamp": "2025-11-13T10:00:00"
      },
      {
        "station_name": "Tumana Bridge",
        "location": "Marikina River - Tumana",
        "coordinates": {
          "lat": 14.6789,
          "lon": 121.1100
        },
        "water_level_m": 16.2,
        "normal_level_m": 10.8,
        "alert_level_m": 13.8,
        "alarm_level_m": 14.8,
        "critical_level_m": 16.8,
        "status": "alarm",
        "status_code": 2,
        "risk_score": 0.8,
        "trend": "rising",
        "change_rate_m_per_hour": 0.4,
        "timestamp": "2025-11-13T10:00:00"
      },
      {
        "station_name": "Montalban",
        "location": "Wawa Dam - Montalban",
        "coordinates": {
          "lat": 14.7289,
          "lon": 121.1456
        },
        "water_level_m": 20.5,
        "normal_level_m": 14.0,
        "alert_level_m": 17.0,
        "alarm_level_m": 18.5,
        "critical_level_m": 20.0,
        "status": "critical",
        "status_code": 3,
        "risk_score": 1.0,
        "trend": "rising",
        "change_rate_m_per_hour": 0.7,
        "timestamp": "2025-11-13T10:00:00"
      },
      {
        "station_name": "Rosario Bridge",
        "location": "Pasig River - Rosario",
        "coordinates": {
          "lat": 14.6175,
          "lon": 121.0842
        },
        "water_level_m": 12.8,
        "normal_level_m": 8.5,
        "alert_level_m": 10.5,
        "alarm_level_m": 11.5,
        "critical_level_m": 13.0,
        "status": "alarm",
        "status_code": 2,
        "risk_score": 0.8,
        "trend": "rising",
        "change_rate_m_per_hour": 0.3,
        "timestamp": "2025-11-13T10:00:00"
      }
    ]
  },

  "weather_data": {
    "metadata": {
      "source": "OpenWeatherMap API",
      "location": "Marikina City",
      "coordinates": {
        "lat": 14.6507,
        "lon": 121.1029
      },
      "last_update": "2025-11-13T10:00:00"
    },
    "current": {
      "temperature_c": 26.5,
      "feels_like_c": 30.2,
      "humidity_percent": 95,
      "pressure_hpa": 1005,
      "wind_speed_kph": 45.0,
      "wind_direction_deg": 135,
      "wind_gust_kph": 65.0,
      "rainfall_1h_mm": 80.0,
      "rainfall_3h_mm": 180.0,
      "visibility_km": 2.0,
      "cloud_cover_percent": 100,
      "weather_main": "Rain",
      "weather_description": "Heavy intensity rain",
      "weather_intensity": "intense",
      "timestamp": "2025-11-13T10:00:00"
    },
    "forecast_24h": {
      "total_rainfall_mm": 350.0,
      "max_temperature_c": 28.0,
      "min_temperature_c": 24.0,
      "max_wind_speed_kph": 75.0,
      "weather_description": "Torrential rain with strong winds",
      "alert_level": "red",
      "warnings": [
        "Typhoon warning in effect",
        "Flood advisory issued",
        "Strong wind advisory"
      ]
    }
  },

  "dam_levels": {
    "metadata": {
      "source": "PAGASA Dam Monitoring",
      "dams_total": 3,
      "last_update": "2025-11-13T09:00:00"
    },
    "dams": [
      {
        "dam_name": "Angat Dam",
        "location": "Bulacan",
        "reservoir_water_level_m": 212.5,
        "normal_high_water_level_m": 210.0,
        "rule_curve_elevation_m": 210.5,
        "spilling_level_m": 212.0,
        "deviation_from_nhwl_m": 2.5,
        "deviation_from_rule_curve_m": 2.0,
        "status": "critical",
        "status_code": 3,
        "risk_score": 1.0,
        "water_level_change_hr": "+0.8m",
        "gate_openings": 2,
        "discharge_rate_m3_per_s": 850.0,
        "inflow_rate_m3_per_s": 1200.0,
        "timestamp": "2025-11-13T09:00:00"
      },
      {
        "dam_name": "La Mesa Dam",
        "location": "Quezon City",
        "reservoir_water_level_m": 81.5,
        "normal_high_water_level_m": 80.15,
        "rule_curve_elevation_m": 80.5,
        "spilling_level_m": 80.8,
        "deviation_from_nhwl_m": 1.35,
        "deviation_from_rule_curve_m": 1.0,
        "status": "alarm",
        "status_code": 2,
        "risk_score": 0.8,
        "water_level_change_hr": "+0.5m",
        "gate_openings": 1,
        "discharge_rate_m3_per_s": 45.0,
        "inflow_rate_m3_per_s": 85.0,
        "timestamp": "2025-11-13T09:00:00"
      },
      {
        "dam_name": "Ipo Dam",
        "location": "Norzagaray, Bulacan",
        "reservoir_water_level_m": 101.8,
        "normal_high_water_level_m": 100.8,
        "rule_curve_elevation_m": 101.0,
        "spilling_level_m": 101.5,
        "deviation_from_nhwl_m": 1.0,
        "deviation_from_rule_curve_m": 0.8,
        "status": "alarm",
        "status_code": 2,
        "risk_score": 0.8,
        "water_level_change_hr": "+0.4m",
        "gate_openings": 1,
        "discharge_rate_m3_per_s": 320.0,
        "inflow_rate_m3_per_s": 580.0,
        "timestamp": "2025-11-13T09:00:00"
      }
    ]
  },

  "risk_assessment": {
    "overall_risk_level": "critical",
    "risk_score": 0.95,
    "flood_probability": 0.98,
    "affected_areas": [
      "Nangka",
      "Sto. Niño",
      "Tumana",
      "Concepcion",
      "Malanday"
    ],
    "recommendations": [
      "Immediate evacuation recommended for low-lying areas",
      "All major roads expected to be impassable within 2 hours",
      "Dam water releases will increase river levels further"
    ]
  }
}
```

---

## 📄 Template: flood_simulation_scenario_2.json

**Scenario:** Moderate Flooding - Monsoon Rain

```json
{
  "scenario_name": "Moderate Flooding - Monsoon Rain",
  "scenario_id": 2,
  "description": "Sustained monsoon rain causing moderate flooding in low-lying areas",
  "start_time": "2025-11-12T14:00:00",
  "duration_hours": 8,
  "severity": "moderate",

  "river_levels": {
    "metadata": {
      "source": "PAGASA River Level Monitoring",
      "stations_total": 17,
      "last_update": "2025-11-12T16:00:00"
    },
    "stations": [
      {
        "station_name": "Sto Nino",
        "location": "Marikina River - Sto. Niño Bridge",
        "coordinates": {
          "lat": 14.6553,
          "lon": 121.0967
        },
        "water_level_m": 15.8,
        "normal_level_m": 12.0,
        "alert_level_m": 15.0,
        "alarm_level_m": 16.0,
        "critical_level_m": 18.0,
        "status": "alert",
        "status_code": 1,
        "risk_score": 0.5,
        "trend": "rising",
        "change_rate_m_per_hour": 0.2,
        "timestamp": "2025-11-12T16:00:00"
      },
      {
        "station_name": "Nangka",
        "location": "Marikina River - Nangka",
        "coordinates": {
          "lat": 14.6507,
          "lon": 121.1009
        },
        "water_level_m": 15.2,
        "normal_level_m": 11.5,
        "alert_level_m": 14.5,
        "alarm_level_m": 15.5,
        "critical_level_m": 17.5,
        "status": "alert",
        "status_code": 1,
        "risk_score": 0.5,
        "trend": "rising",
        "change_rate_m_per_hour": 0.2,
        "timestamp": "2025-11-12T16:00:00"
      },
      {
        "station_name": "Tumana Bridge",
        "location": "Marikina River - Tumana",
        "coordinates": {
          "lat": 14.6789,
          "lon": 121.1100
        },
        "water_level_m": 14.2,
        "normal_level_m": 10.8,
        "alert_level_m": 13.8,
        "alarm_level_m": 14.8,
        "critical_level_m": 16.8,
        "status": "alert",
        "status_code": 1,
        "risk_score": 0.5,
        "trend": "stable",
        "change_rate_m_per_hour": 0.1,
        "timestamp": "2025-11-12T16:00:00"
      },
      {
        "station_name": "Montalban",
        "location": "Wawa Dam - Montalban",
        "coordinates": {
          "lat": 14.7289,
          "lon": 121.1456
        },
        "water_level_m": 17.5,
        "normal_level_m": 14.0,
        "alert_level_m": 17.0,
        "alarm_level_m": 18.5,
        "critical_level_m": 20.0,
        "status": "alert",
        "status_code": 1,
        "risk_score": 0.5,
        "trend": "rising",
        "change_rate_m_per_hour": 0.2,
        "timestamp": "2025-11-12T16:00:00"
      },
      {
        "station_name": "Rosario Bridge",
        "location": "Pasig River - Rosario",
        "coordinates": {
          "lat": 14.6175,
          "lon": 121.0842
        },
        "water_level_m": 10.8,
        "normal_level_m": 8.5,
        "alert_level_m": 10.5,
        "alarm_level_m": 11.5,
        "critical_level_m": 13.0,
        "status": "alert",
        "status_code": 1,
        "risk_score": 0.5,
        "trend": "rising",
        "change_rate_m_per_hour": 0.1,
        "timestamp": "2025-11-12T16:00:00"
      }
    ]
  },

  "weather_data": {
    "metadata": {
      "source": "OpenWeatherMap API",
      "location": "Marikina City",
      "coordinates": {
        "lat": 14.6507,
        "lon": 121.1029
      },
      "last_update": "2025-11-12T16:00:00"
    },
    "current": {
      "temperature_c": 28.0,
      "feels_like_c": 32.5,
      "humidity_percent": 85,
      "pressure_hpa": 1010,
      "wind_speed_kph": 25.0,
      "wind_direction_deg": 90,
      "wind_gust_kph": 35.0,
      "rainfall_1h_mm": 30.0,
      "rainfall_3h_mm": 75.0,
      "visibility_km": 5.0,
      "cloud_cover_percent": 90,
      "weather_main": "Rain",
      "weather_description": "Moderate rain",
      "weather_intensity": "moderate",
      "timestamp": "2025-11-12T16:00:00"
    },
    "forecast_24h": {
      "total_rainfall_mm": 120.0,
      "max_temperature_c": 30.0,
      "min_temperature_c": 26.0,
      "max_wind_speed_kph": 35.0,
      "weather_description": "Continued moderate rain",
      "alert_level": "orange",
      "warnings": [
        "Flood advisory for low-lying areas",
        "Moderate rain expected for next 12 hours"
      ]
    }
  },

  "dam_levels": {
    "metadata": {
      "source": "PAGASA Dam Monitoring",
      "dams_total": 3,
      "last_update": "2025-11-12T15:00:00"
    },
    "dams": [
      {
        "dam_name": "Angat Dam",
        "location": "Bulacan",
        "reservoir_water_level_m": 210.8,
        "normal_high_water_level_m": 210.0,
        "rule_curve_elevation_m": 210.5,
        "spilling_level_m": 212.0,
        "deviation_from_nhwl_m": 0.8,
        "deviation_from_rule_curve_m": 0.3,
        "status": "alert",
        "status_code": 1,
        "risk_score": 0.5,
        "water_level_change_hr": "+0.3m",
        "gate_openings": 0,
        "discharge_rate_m3_per_s": 150.0,
        "inflow_rate_m3_per_s": 350.0,
        "timestamp": "2025-11-12T15:00:00"
      },
      {
        "dam_name": "La Mesa Dam",
        "location": "Quezon City",
        "reservoir_water_level_m": 80.5,
        "normal_high_water_level_m": 80.15,
        "rule_curve_elevation_m": 80.5,
        "spilling_level_m": 80.8,
        "deviation_from_nhwl_m": 0.35,
        "deviation_from_rule_curve_m": 0.0,
        "status": "watch",
        "status_code": 0,
        "risk_score": 0.3,
        "water_level_change_hr": "+0.2m",
        "gate_openings": 0,
        "discharge_rate_m3_per_s": 15.0,
        "inflow_rate_m3_per_s": 35.0,
        "timestamp": "2025-11-12T15:00:00"
      },
      {
        "dam_name": "Ipo Dam",
        "location": "Norzagaray, Bulacan",
        "reservoir_water_level_m": 101.2,
        "normal_high_water_level_m": 100.8,
        "rule_curve_elevation_m": 101.0,
        "spilling_level_m": 101.5,
        "deviation_from_nhwl_m": 0.4,
        "deviation_from_rule_curve_m": 0.2,
        "status": "watch",
        "status_code": 0,
        "risk_score": 0.3,
        "water_level_change_hr": "+0.2m",
        "gate_openings": 0,
        "discharge_rate_m3_per_s": 80.0,
        "inflow_rate_m3_per_s": 150.0,
        "timestamp": "2025-11-12T15:00:00"
      }
    ]
  },

  "risk_assessment": {
    "overall_risk_level": "moderate",
    "risk_score": 0.55,
    "flood_probability": 0.65,
    "affected_areas": [
      "Nangka",
      "Tumana",
      "Low-lying sections of JP Rizal"
    ],
    "recommendations": [
      "Monitor river levels closely",
      "Prepare for potential evacuation in low-lying areas",
      "Avoid unnecessary travel through flood-prone roads"
    ]
  }
}
```

---

## 📄 Template: flood_simulation_scenario_3.json

**Scenario:** Light Flooding - Normal Rain

```json
{
  "scenario_name": "Light Flooding - Normal Rain",
  "scenario_id": 3,
  "description": "Light to moderate rain with minimal flooding impact",
  "start_time": "2025-11-11T10:00:00",
  "duration_hours": 4,
  "severity": "low",

  "river_levels": {
    "metadata": {
      "source": "PAGASA River Level Monitoring",
      "stations_total": 17,
      "last_update": "2025-11-11T12:00:00"
    },
    "stations": [
      {
        "station_name": "Sto Nino",
        "location": "Marikina River - Sto. Niño Bridge",
        "coordinates": {
          "lat": 14.6553,
          "lon": 121.0967
        },
        "water_level_m": 13.2,
        "normal_level_m": 12.0,
        "alert_level_m": 15.0,
        "alarm_level_m": 16.0,
        "critical_level_m": 18.0,
        "status": "normal",
        "status_code": 0,
        "risk_score": 0.2,
        "trend": "stable",
        "change_rate_m_per_hour": 0.05,
        "timestamp": "2025-11-11T12:00:00"
      },
      {
        "station_name": "Nangka",
        "location": "Marikina River - Nangka",
        "coordinates": {
          "lat": 14.6507,
          "lon": 121.1009
        },
        "water_level_m": 12.8,
        "normal_level_m": 11.5,
        "alert_level_m": 14.5,
        "alarm_level_m": 15.5,
        "critical_level_m": 17.5,
        "status": "normal",
        "status_code": 0,
        "risk_score": 0.2,
        "trend": "stable",
        "change_rate_m_per_hour": 0.05,
        "timestamp": "2025-11-11T12:00:00"
      },
      {
        "station_name": "Tumana Bridge",
        "location": "Marikina River - Tumana",
        "coordinates": {
          "lat": 14.6789,
          "lon": 121.1100
        },
        "water_level_m": 11.5,
        "normal_level_m": 10.8,
        "alert_level_m": 13.8,
        "alarm_level_m": 14.8,
        "critical_level_m": 16.8,
        "status": "normal",
        "status_code": 0,
        "risk_score": 0.2,
        "trend": "stable",
        "change_rate_m_per_hour": 0.03,
        "timestamp": "2025-11-11T12:00:00"
      },
      {
        "station_name": "Montalban",
        "location": "Wawa Dam - Montalban",
        "coordinates": {
          "lat": 14.7289,
          "lon": 121.1456
        },
        "water_level_m": 14.8,
        "normal_level_m": 14.0,
        "alert_level_m": 17.0,
        "alarm_level_m": 18.5,
        "critical_level_m": 20.0,
        "status": "normal",
        "status_code": 0,
        "risk_score": 0.2,
        "trend": "stable",
        "change_rate_m_per_hour": 0.05,
        "timestamp": "2025-11-11T12:00:00"
      },
      {
        "station_name": "Rosario Bridge",
        "location": "Pasig River - Rosario",
        "coordinates": {
          "lat": 14.6175,
          "lon": 121.0842
        },
        "water_level_m": 9.2,
        "normal_level_m": 8.5,
        "alert_level_m": 10.5,
        "alarm_level_m": 11.5,
        "critical_level_m": 13.0,
        "status": "normal",
        "status_code": 0,
        "risk_score": 0.2,
        "trend": "stable",
        "change_rate_m_per_hour": 0.02,
        "timestamp": "2025-11-11T12:00:00"
      }
    ]
  },

  "weather_data": {
    "metadata": {
      "source": "OpenWeatherMap API",
      "location": "Marikina City",
      "coordinates": {
        "lat": 14.6507,
        "lon": 121.1029
      },
      "last_update": "2025-11-11T12:00:00"
    },
    "current": {
      "temperature_c": 30.0,
      "feels_like_c": 34.5,
      "humidity_percent": 70,
      "pressure_hpa": 1012,
      "wind_speed_kph": 15.0,
      "wind_direction_deg": 45,
      "wind_gust_kph": 20.0,
      "rainfall_1h_mm": 10.0,
      "rainfall_3h_mm": 25.0,
      "visibility_km": 10.0,
      "cloud_cover_percent": 60,
      "weather_main": "Rain",
      "weather_description": "Light rain",
      "weather_intensity": "light",
      "timestamp": "2025-11-11T12:00:00"
    },
    "forecast_24h": {
      "total_rainfall_mm": 35.0,
      "max_temperature_c": 32.0,
      "min_temperature_c": 28.0,
      "max_wind_speed_kph": 20.0,
      "weather_description": "Partly cloudy with occasional light rain",
      "alert_level": "green",
      "warnings": []
    }
  },

  "dam_levels": {
    "metadata": {
      "source": "PAGASA Dam Monitoring",
      "dams_total": 3,
      "last_update": "2025-11-11T11:00:00"
    },
    "dams": [
      {
        "dam_name": "Angat Dam",
        "location": "Bulacan",
        "reservoir_water_level_m": 209.5,
        "normal_high_water_level_m": 210.0,
        "rule_curve_elevation_m": 210.5,
        "spilling_level_m": 212.0,
        "deviation_from_nhwl_m": -0.5,
        "deviation_from_rule_curve_m": -1.0,
        "status": "normal",
        "status_code": 0,
        "risk_score": 0.1,
        "water_level_change_hr": "+0.1m",
        "gate_openings": 0,
        "discharge_rate_m3_per_s": 50.0,
        "inflow_rate_m3_per_s": 80.0,
        "timestamp": "2025-11-11T11:00:00"
      },
      {
        "dam_name": "La Mesa Dam",
        "location": "Quezon City",
        "reservoir_water_level_m": 79.8,
        "normal_high_water_level_m": 80.15,
        "rule_curve_elevation_m": 80.5,
        "spilling_level_m": 80.8,
        "deviation_from_nhwl_m": -0.35,
        "deviation_from_rule_curve_m": -0.7,
        "status": "normal",
        "status_code": 0,
        "risk_score": 0.1,
        "water_level_change_hr": "+0.05m",
        "gate_openings": 0,
        "discharge_rate_m3_per_s": 5.0,
        "inflow_rate_m3_per_s": 12.0,
        "timestamp": "2025-11-11T11:00:00"
      },
      {
        "dam_name": "Ipo Dam",
        "location": "Norzagaray, Bulacan",
        "reservoir_water_level_m": 100.5,
        "normal_high_water_level_m": 100.8,
        "rule_curve_elevation_m": 101.0,
        "spilling_level_m": 101.5,
        "deviation_from_nhwl_m": -0.3,
        "deviation_from_rule_curve_m": -0.5,
        "status": "normal",
        "status_code": 0,
        "risk_score": 0.1,
        "water_level_change_hr": "+0.05m",
        "gate_openings": 0,
        "discharge_rate_m3_per_s": 30.0,
        "inflow_rate_m3_per_s": 50.0,
        "timestamp": "2025-11-11T11:00:00"
      }
    ]
  },

  "risk_assessment": {
    "overall_risk_level": "low",
    "risk_score": 0.15,
    "flood_probability": 0.20,
    "affected_areas": [],
    "recommendations": [
      "Normal operations - no flood risk",
      "Continue monitoring weather conditions"
    ]
  }
}
```

---

## 🗺️ Status Code Reference

### **River Level Status**
| Code | Status | Water Level | Risk Score |
|------|--------|-------------|-----------|
| 0 | Normal | < Alert level | 0.0-0.3 |
| 1 | Alert | Alert ≤ level < Alarm | 0.4-0.6 |
| 2 | Alarm | Alarm ≤ level < Critical | 0.7-0.9 |
| 3 | Critical | ≥ Critical level | 0.9-1.0 |

### **Dam Status**
| Code | Status | Deviation from NHWL | Risk Score |
|------|--------|-------------------|-----------|
| 0 | Normal | < 0.5m | 0.0-0.2 |
| 1 | Watch/Alert | 0.5-1.0m | 0.3-0.5 |
| 2 | Alarm | 1.0-2.0m | 0.6-0.8 |
| 3 | Critical | > 2.0m | 0.9-1.0 |

### **Weather Intensity**
| Intensity | Rainfall (mm/hr) | PAGASA Classification |
|-----------|-----------------|----------------------|
| Light | 0.1-10 | Light rain |
| Moderate | 10-30 | Moderate rain |
| Heavy | 30-80 | Heavy rain |
| Intense | 80-200 | Intense rain |
| Torrential | > 200 | Torrential rain |

---

## 📊 How FloodAgent Uses This Data

1. **Load Simulation File**
   ```python
   flood_agent = FloodAgent(
       agent_id="flood_001",
       use_simulated=True,
       scenario=1  # Loads flood_simulation_scenario_1.json
   )
   ```

2. **Extract Data**
   - River levels → `flood_agent.river_levels`
   - Weather → `flood_agent.weather_data`
   - Dams → `flood_agent.dam_levels`

3. **Forward to HazardAgent**
   ```python
   flood_agent.send_to_hazard_agent({
       "Sto Nino": {
           "water_level_m": 18.5,
           "status": "critical",
           "risk_score": 1.0
       },
       "Marikina_weather": {
           "rainfall_1h_mm": 80.0,
           "rainfall_24h_mm": 350.0
       }
   })
   ```

4. **HazardAgent Processes**
   - Fuses with ScoutAgent data
   - Calculates risk scores
   - Updates graph edges

---

## ✅ Validation Checklist

Before using simulation data, verify:

- [ ] All river stations have valid coordinates
- [ ] Water levels follow logical progression (normal < alert < alarm < critical)
- [ ] Status codes match water level thresholds
- [ ] Timestamps are consistent within scenario
- [ ] Risk scores align with severity (0.0-1.0 scale)
- [ ] Weather data has complete current + forecast fields
- [ ] Dam levels have NHWL and deviation calculations
- [ ] Scenario severity matches data values (low/moderate/critical)

---

## 🎯 Quick Reference

### **Marikina River Alert Levels**

| Station | Normal (m) | Alert (m) | Alarm (m) | Critical (m) |
|---------|-----------|----------|----------|-------------|
| Sto Nino | 12.0 | 15.0 | 16.0 | 18.0 |
| Nangka | 11.5 | 14.5 | 15.5 | 17.5 |
| Tumana | 10.8 | 13.8 | 14.8 | 16.8 |
| Montalban | 14.0 | 17.0 | 18.5 | 20.0 |

*Source: PAGASA Flood Forecasting and Warning System*

---

**Next:** See `SCOUT_SIMULATION_GUIDE.md` for ScoutAgent data format
