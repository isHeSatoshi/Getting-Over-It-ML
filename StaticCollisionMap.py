import json
import os
import math
from PIL import Image

class StaticCollisionMap:
    def __init__(self, project_dir):
        self.project_dir = project_dir
        self.project_json_path = os.path.join(project_dir, "assets", "project.json")
        self.assets_dir = os.path.join(project_dir, "assets")
        self.tiles = {}
        self.load_project_assets()
        
    def load_project_assets(self):
        if not os.path.exists(self.project_json_path):
            raise FileNotFoundError(f"Project JSON not found at {self.project_json_path}")
            
        with open(self.project_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        targets = data.get("targets", [])
        level_target = next((t for t in targets if t.get("name") == "Level"), None)
        if not level_target:
            raise ValueError("Level target not found in project.json")
            
        costumes = level_target.get("costumes", [])
        for c in costumes:
            name = c.get("name")
            if not name or name == "blank":
                continue
                
            try:
                parts = name.split("x")
                lx = int(parts[0])
                ly = int(parts[1])
            except Exception:
                continue
                
            asset_id = c.get("assetId")
            data_format = c.get("dataFormat")
            asset_path = os.path.join(self.assets_dir, f"{asset_id}.{data_format}")
            
            if os.path.exists(asset_path):
                img = Image.open(asset_path).convert("RGBA")
                cx = c.get("rotationCenterX", 480)
                cy = c.get("rotationCenterY", 360)
                self.tiles[(lx, ly)] = {
                    "name": name,
                    "image": img,
                    "cx": cx,
                    "cy": cy,
                    "width": img.width,
                    "height": img.height
                }
        print(f"Loaded {len(self.tiles)} collision tiles.")

    def check_collision(self, wx, wy):
        # Tile world position is exactly (lx*464, ly*344) per the game's
        # `position it` block (Level sprite, block og -> fn). No Y offset.
        # The previous +5 / -5 shift was a bug that mis-sampled every ray/ledge.
        lx = round(wx / 464.0)
        ly = round(wy / 344.0)

        tile_key = (lx, ly)
        if tile_key not in self.tiles:
            return False

        tile = self.tiles[tile_key]
        local_x = wx - (lx * 464.0)
        local_y = wy - (ly * 344.0)
        
        # Scale to double-resolution costume sizes
        pixel_x = int(round(local_x * 2.0 + tile["cx"]))
        pixel_y = int(round(tile["cy"] - local_y * 2.0))
        
        if pixel_x < 0 or pixel_x >= tile["width"] or pixel_y < 0 or pixel_y >= tile["height"]:
            return False
            
        r, g, b, a = tile["image"].getpixel((pixel_x, pixel_y))
        return a > 0

    def raycast(self, ox, oy, theta, max_dist=150.0):
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)
        
        # 1. March outward first in steps of 5 pixels
        hit_dist = None
        step_size = 5.0
        d = 0.0
        while d <= max_dist:
            qx = ox + d * cos_t
            qy = oy + d * sin_t
            if self.check_collision(qx, qy):
                hit_dist = d
                break
            d += step_size
            
        # Check end of the ray if no hit found
        if hit_dist is None:
            if self.check_collision(ox + max_dist * cos_t, oy + max_dist * sin_t):
                hit_dist = max_dist
            else:
                return None
                
        # 2. Binary search to refine the hit point boundary
        lo = max(0.0, hit_dist - step_size)
        hi = hit_dist
        for _ in range(6):
            mid = (lo + hi) / 2.0
            if self.check_collision(ox + mid * cos_t, oy + mid * sin_t):
                hi = mid
            else:
                lo = mid
                
        refined_dist = hi
        hx = ox + refined_dist * cos_t
        hy = oy + refined_dist * sin_t
        
        # 3. Compute normal numerically
        eps = 3.0
        c_R = 1 if self.check_collision(hx + eps, hy) else 0
        c_L = 1 if self.check_collision(hx - eps, hy) else 0
        c_U = 1 if self.check_collision(hx, hy + eps) else 0
        c_D = 1 if self.check_collision(hx, hy - eps) else 0
        
        nx = c_L - c_R
        ny = c_D - c_U
        length = math.hypot(nx, ny)
        if length > 0:
            nx /= length
            ny /= length
        else:
            nx = -cos_t
            ny = -sin_t
            
        # 4. Check clearance above hit point
        clearance = 1.0
        for dy in [5.0, 10.0, 15.0]:
            if self.check_collision(hx, hy + dy):
                clearance = 0.0
                break
                
        return {
            "dist": refined_dist,
            "hx": hx,
            "hy": hy,
            "nx": nx,
            "ny": ny,
            "clearance": clearance
        }

    def get_terrain_descriptor(self, px, py, hx, hy):
        num_rays = 16
        max_dist = 150.0
        rays = []
        ledges = []
        
        # Rays from Pot (px, py)
        for i in range(num_rays):
            theta = (i * 2 * math.pi) / num_rays
            hit = self.raycast(px, py, theta, max_dist)
            if hit:
                rays.append([hit["dist"], hit["nx"], hit["ny"], 1.0])
                if hit["ny"] > 0.3 and hit["clearance"] > 0.5:
                    ledges.append({
                        "dx": hit["hx"] - px,
                        "dy": hit["hy"] - py,
                        "nx": hit["nx"],
                        "ny": hit["ny"],
                        "clearance": 1.0,
                        "dist": math.hypot(hit["hx"] - px, hit["hy"] - py)
                    })
            else:
                rays.append([max_dist, 0.0, 0.0, 0.0])
                
        # Rays from Hammer (hx, hy)
        for i in range(num_rays):
            theta = (i * 2 * math.pi) / num_rays
            hit = self.raycast(hx, hy, theta, max_dist)
            if hit:
                rays.append([hit["dist"], hit["nx"], hit["ny"], 1.0])
                if hit["ny"] > 0.3 and hit["clearance"] > 0.5:
                    ledges.append({
                        "dx": hit["hx"] - px,
                        "dy": hit["hy"] - py,
                        "nx": hit["nx"],
                        "ny": hit["ny"],
                        "clearance": 1.0,
                        "dist": math.hypot(hit["hx"] - px, hit["hy"] - py)
                    })
            else:
                rays.append([max_dist, 0.0, 0.0, 0.0])
                
        # Sort ledges by distance and take top 8
        ledges.sort(key=lambda l: l["dist"])
        top_ledges = []
        for l in ledges[:8]:
            top_ledges.append([l["dx"], l["dy"], l["nx"], l["ny"], l["clearance"]])
            
        # Pad to 8 ledges if needed
        while len(top_ledges) < 8:
            top_ledges.append([0.0, 0.0, 0.0, 0.0, 0.0])
            
        return rays, top_ledges
