
import csv
import math
import os
from dataclasses import dataclass, field
from typing import Optional, List, Tuple, Dict

@dataclass
class Runway:
    le_ident: str
    he_ident: str
    length: int
    surface: str

@dataclass
class Airport:
    icao: str
    name: str
    lat: float
    lon: float
    elevation: float
    type: str
    runways: List[Runway] = field(default_factory=list)

class AirportManager:
    """Manages airport database and spatial lookups."""
    
    def __init__(self, airports_csv: str, runways_csv: str):
        self.airports_csv = airports_csv
        self.runways_csv = runways_csv
        self._airports: Dict[str, Airport] = {}
        self._loaded = False

    def load(self):
        """Load airports and runways from CSV."""
        if self._loaded:
            return
        
        if not os.path.exists(self.airports_csv):
            return

        try:
            # 1. Load Airports
            with open(self.airports_csv, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Filter for airports likely to have ATC
                    if row['type'] not in ('medium_airport', 'large_airport'):
                        continue
                        
                    try:
                        icao = row['ident']
                        self._airports[icao] = Airport(
                            icao=icao,
                            name=row['name'],
                            lat=float(row['latitude_deg']),
                            lon=float(row['longitude_deg']),
                            elevation=float(row['elevation_ft']) if row['elevation_ft'] else 0.0,
                            type=row['type'],
                            runways=[]
                        )
                    except (ValueError, KeyError):
                        continue
            
            # 2. Load Runways if possible
            if os.path.exists(self.runways_csv):
                with open(self.runways_csv, mode='r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        icao = row['airport_ident']
                        if icao in self._airports:
                            try:
                                self._airports[icao].runways.append(Runway(
                                    le_ident=row['le_ident'],
                                    he_ident=row['he_ident'],
                                    length=int(row['length_ft']) if row['length_ft'] else 0,
                                    surface=row['surface']
                                ))
                            except (ValueError, KeyError):
                                continue
                                
            self._loaded = True
        except Exception:
            pass


    def find_nearest(self, lat: float, lon: float, max_dist_nm: float = 50.0) -> Optional[Airport]:
        """Find the nearest airport within max_dist_nm."""
        if not self._loaded:
            self.load()

        nearest = None
        min_dist = float('inf')

        for apt in self._airports.values():
            dist = self._calculate_distance(lat, lon, apt.lat, apt.lon)
            if dist < min_dist and dist <= max_dist_nm:
                min_dist = dist
                nearest = apt

        return nearest

    def _calculate_distance(self, lat1, lon1, lat2, lon2) -> float:
        """Haversine distance in nautical miles."""
        R = 3440.065  # Earth radius in nautical miles
        
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lon2 - lon1)
        
        a = math.sin(dphi/2)**2 + \
            math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
