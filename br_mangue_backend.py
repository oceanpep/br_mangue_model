import numpy as np
import rasterio
from rasterio.enums import Resampling
import geopandas as gpd
from rasterio.features import rasterize
from shapely.geometry import mapping

# CONSTANTES - CLASSES DE USO DA TERRA
MANGUE = 1
VEGETACAO_TERRESTRE = 2
MAR = 3
AREA_ANTROPIZADA = 4
SOLO_DESCOBERTO = 5
SOLO_DESCOBERTO_INUNDADO = 6
AREA_ANTROPIZADA_INUNDADO = 7
MANGUE_MIGRADO = 8
MANGUE_INUNDADO = 9
VEGETACAO_TERRESTRE_INUNDADO = 10

# CONSTANTES - CLASSES DE SOLO
SOLO_MANGUE = 3
SOLO_MANGUE_MIGRADO = 9

CANAL_FLUVIAL = 0

# Mapeamento: código de uso -> campo no model
uso_map = {
    MAR: "areaMar_USO",
    MANGUE: "areaMangueRemanescente_USO",
    MANGUE_INUNDADO: "areaMangueInundado_USO",
    MANGUE_MIGRADO: "areaMangueMigrado_USO",
    AREA_ANTROPIZADA: "areaAntropizada_USO",
    AREA_ANTROPIZADA_INUNDADO: "areaAntropizadaInundada_USO",
    SOLO_DESCOBERTO: "areaSoloDescoberto_USO",
    SOLO_DESCOBERTO_INUNDADO: "areaSoloDescobertoInundado_USO",
    VEGETACAO_TERRESTRE: "areaVegetacao_USO",
    VEGETACAO_TERRESTRE_INUNDADO: "areaVegetacaoInundado_USO"
}

def inicializa(model_data):
    for campo in uso_map.values():
        model_data[campo] = 0

def contagem(model_data, cell_space_usos, area_celula):
    inicializa(model_data)

    unique_uses, counts = np.unique(cell_space_usos, return_counts=True)

    for i, uso_val in enumerate(unique_uses):
        if uso_val in uso_map:
            campo = uso_map[uso_val]
            model_data[campo] += counts[i] * area_celula

    model_data["total_USO"] = sum(model_data[campo] for campo in uso_map.values())

def is_sea_or_flooded(uso):
    return uso == MAR or \
           uso == SOLO_DESCOBERTO_INUNDADO or \
           uso == AREA_ANTROPIZADA_INUNDADO or \
           uso == MANGUE_INUNDADO or \
           uso == VEGETACAO_TERRESTRE_INUNDADO

def apply_flooding(cell_uso):
    if cell_uso == MANGUE:
        return MANGUE_INUNDADO
    elif cell_uso == VEGETACAO_TERRESTRE:
        return VEGETACAO_TERRESTRE_INUNDADO
    elif cell_uso == AREA_ANTROPIZADA:
        return AREA_ANTROPIZADA_INUNDADO
    elif cell_uso == SOLO_DESCOBERTO:
        return SOLO_DESCOBERTO_INUNDADO
    else:
        return cell_uso

class CellularSpace:
    def __init__(self, usos_data, alt_data, solos_data, cell_size):
        self.usos = usos_data.astype(int)
        self.alt = alt_data.astype(float)
        self.solos = solos_data.astype(int)
        self.rows, self.cols = self.usos.shape
        self.cell_size = cell_size

        self.usos_past = np.copy(self.usos)
        self.alt_past = np.copy(self.alt)
        self.solos_past = np.copy(self.solos)

    def synchronize(self):
        self.usos_past = np.copy(self.usos)
        self.alt_past = np.copy(self.alt)
        self.solos_past = np.copy(self.solos)

    def get_cell_properties(self, r, c):
        return {
            "Usos": self.usos[r, c],
            "Alt2": self.alt[r, c],
            "ClasseSolos": self.solos[r, c],
            "past": {
                "Usos": self.usos_past[r, c],
                "Alt2": self.alt_past[r, c],
                "ClasseSolos": self.solos_past[r, c]
            }
        }

    def set_cell_property(self, r, c, prop_name, value):
        if prop_name == "Usos":
            self.usos[r, c] = value
        elif prop_name == "Alt2":
            self.alt[r, c] = value
        elif prop_name == "ClasseSolos":
            self.solos[r, c] = value

    def for_each_cell(self, func):
        for r in range(self.rows):
            for c in range(self.cols):
                func(r, c, self.get_cell_properties(r, c))

    def for_each_neighbor(self, r, c, func, moore_self=False):
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if not moore_self and dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    func(nr, nc, self.get_cell_properties(nr, nc))

class BrMangueModel:
    def __init__(self, usos_data, alt_data, solos_data, area_celula=0.09,
                 tide_height=6, sea_level_rise_rate=0.5, final_time=100):
        self.cell_space = CellularSpace(usos_data, alt_data, solos_data, area_celula)
        self.area_celula = area_celula
        self.tide_height = tide_height
        self.sea_level_rise_rate = sea_level_rise_rate
        self.final_time = final_time
        self.current_time = 0

        self.model_data = {}
        inicializa(self.model_data)

        self.simulation_results = {
            "time": [],
            "areaVegetacao_USO": [],
            "areaVegetacaoInundado_USO": [],
            "total_USO": []
        }

    def _apply_flooding_logic(self, r, c, cell):
        cell_uso_past = cell["past"]["Usos"]
        cell_alt_past = cell["past"]["Alt2"]

        if is_sea_or_flooded(cell_uso_past) and cell_alt_past >= 0:
            neighbor_coords = []
            neighbor_alts_past = []
            neighbor_usos_past = []

            for dr in [-1, 0, 1]:
                for dc in [-1, 0, 1]:
                    if dr == 0 and dc == 0: continue
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < self.cell_space.rows and 0 <= nc < self.cell_space.cols:
                        neighbor_coords.append((nr, nc))
                        neighbor_alts_past.append(self.cell_space.alt_past[nr, nc])
                        neighbor_usos_past.append(self.cell_space.usos_past[nr, nc])

            neighbor_alts_past = np.array(neighbor_alts_past)

            lower_alt_neighbors_mask = neighbor_alts_past < cell_alt_past
            num_lower_alt_neighbors = np.sum(lower_alt_neighbors_mask)

            neighbor_count = 1 + num_lower_alt_neighbors
            flow = self.sea_level_rise_rate / neighbor_count

            self.cell_space.set_cell_property(r, c, "Alt2", cell["Alt2"] + flow)

            for i, (nr, nc) in enumerate(neighbor_coords):
                if lower_alt_neighbors_mask[i]:
                    self.cell_space.set_cell_property(nr, nc, "Alt2", self.cell_space.alt[nr, nc] + flow)
                    if not is_sea_or_flooded(neighbor_usos_past[i]):
                        new_uso = apply_flooding(neighbor_usos_past[i])
                        self.cell_space.set_cell_property(nr, nc, "Usos", new_uso)

    def _apply_mangrove_dynamics_logic(self, r, c, cell):
        cell_uso = cell["Usos"]
        cell_alt = cell["Alt2"]
        cell_solos = cell["ClasseSolos"]

        nmrm = self.current_time * self.sea_level_rise_rate
        nmrm_m = nmrm * 1000
        accretion_rate_mm = 1.693 + (0.939 * nmrm_m)
        accretion_rate_m = accretion_rate_mm / 1000

        tidal_influence_zone = self.tide_height + nmrm

        neighbor_coords = []
        neighbor_usos = []
        neighbor_alts = []
        neighbor_solos = []

        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0: continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.cell_space.rows and 0 <= nc < self.cell_space.cols:
                    neighbor_coords.append((nr, nc))
                    neighbor_usos.append(self.cell_space.usos[nr, nc])
                    neighbor_alts.append(self.cell_space.alt[nr, nc])
                    neighbor_solos.append(self.cell_space.solos[nr, nc])

        if cell_solos == SOLO_MANGUE or cell_solos == CANAL_FLUVIAL:
            for i, (nr, nc) in enumerate(neighbor_coords):
                if (neighbor_usos[i] == VEGETACAO_TERRESTRE or neighbor_usos[i] == SOLO_DESCOBERTO) \
                   and (neighbor_solos[i] != SOLO_MANGUE) \
                   and (neighbor_alts[i] <= tidal_influence_zone):
                    self.cell_space.set_cell_property(nr, nc, "ClasseSolos", SOLO_MANGUE_MIGRADO)

        if cell_uso == MANGUE:
            for i, (nr, nc) in enumerate(neighbor_coords):
                if (neighbor_usos[i] == VEGETACAO_TERRESTRE or neighbor_usos[i] == SOLO_DESCOBERTO) \
                   and neighbor_alts[i] <= tidal_influence_zone \
                   and (neighbor_solos[i] == SOLO_MANGUE_MIGRADO or neighbor_solos[i] == SOLO_MANGUE):
                    self.cell_space.set_cell_property(nr, nc, "Usos", MANGUE_MIGRADO)

        if (cell_solos == MANGUE or cell_solos == MANGUE_MIGRADO) \
           and not is_sea_or_flooded(cell_uso):
            self.cell_space.set_cell_property(r, c, "Alt2", cell_alt + accretion_rate_m)

    def run_simulation(self):
        for t in range(self.final_time):
            self.current_time = t + 1
            print(f"ITERAÇÃO: {self.current_time}")

            self.cell_space.for_each_cell(lambda r, c, cell: self._apply_flooding_logic(r, c, cell))
            self.cell_space.for_each_cell(lambda r, c, cell: self._apply_mangrove_dynamics_logic(r, c, cell))

            self.cell_space.synchronize()

            contagem(self.model_data, self.cell_space.usos.flatten(), self.area_celula)
            self.simulation_results["time"].append(self.current_time)
            self.simulation_results["areaVegetacao_USO"].append(self.model_data.get("areaVegetacao_USO", 0))
            self.simulation_results["areaVegetacaoInundado_USO"].append(self.model_data.get("areaVegetacaoInundado_USO", 0))
            self.simulation_results["total_USO"].append(self.model_data.get("total_USO", 0))

        return self.simulation_results

def load_and_rasterize_vector_solos(solos_path, reference_raster_path, soil_attribute_column='ClasseSolos'):
    """
    Carrega um shapefile de solos, verifica o CRS e o rasteriza para a mesma extensão e resolução
    de um raster de referência.

    Args:
        solos_path (str): Caminho para o shapefile de solos.
        reference_raster_path (str): Caminho para um raster de referência (e.g., uso da terra ou altimetria)
                                     para obter a extensão e resolução.
        soil_attribute_column (str): Nome da coluna no shapefile que contém os valores de classe de solo.

    Returns:
        numpy.ndarray: Array rasterizado dos solos.
        rasterio.transform.Affine: Transformação do raster de solos resultante.
        rasterio.crs.CRS: CRS do raster de solos resultante.
    """
    try:
        solos_gdf = gpd.read_file(solos_path)
    except Exception as e:
        raise ValueError(f"Erro ao carregar o shapefile de solos: {e}")

    if not solos_gdf.crs.is_projected:
        raise ValueError(f"O CRS do shapefile de solos ({solos_gdf.crs.to_string()}) não é projetado. "
                         "Por favor, forneça um shapefile com CRS projetado.")

    if soil_attribute_column not in solos_gdf.columns:
        raise ValueError(f"A coluna de atributo '{soil_attribute_column}' não foi encontrada no shapefile de solos.")

    with rasterio.open(reference_raster_path) as ref_src:
        transform = ref_src.transform
        width = ref_src.width
        height = ref_src.height
        crs = ref_src.crs
        bounds = ref_src.bounds

    # Reprojetar o shapefile para o CRS do raster de referência, se necessário
    if solos_gdf.crs != crs:
        solos_gdf = solos_gdf.to_crs(crs)

    # Criar uma lista de tuplas (geometria, valor) para rasterização
    shapes = [(mapping(geom), value) for geom, value in zip(solos_gdf.geometry, solos_gdf[soil_attribute_column])]

    # Rasterizar o shapefile
    # Usamos all_touched=True para incluir todas as células que tocam a geometria
    # e preenchemos com 0 (CANAL_FLUVIAL) onde não há dados de solo definidos
    rasterized_solos = rasterize(
        shapes=shapes,
        out_shape=(height, width),
        transform=transform,
        fill=CANAL_FLUVIAL,  # Valor padrão para áreas sem dados de solo
        all_touched=True, # Inclui todas as células que tocam a geometria
        dtype=np.int32
    )

    return rasterized_solos, transform, crs

def load_and_standardize_rasters(uso_path, alt_path, target_resolution=None):
    """
    Carrega e padroniza rasters de uso e altimetria. Esta função foi modificada para não carregar solos.
    """
    with rasterio.open(uso_path) as src_uso:
        if not src_uso.crs.is_projected:
            raise ValueError(f"O CRS do raster de uso ({src_uso.crs.to_string()}) não é projetado. Por favor, forneça um raster com CRS projetado.")
        uso_data = src_uso.read(1)
        uso_transform = src_uso.transform
        uso_crs = src_uso.crs
        uso_res = src_uso.res

    with rasterio.open(alt_path) as src_alt:
        if not src_alt.crs.is_projected:
            raise ValueError(f"O CRS do raster de altimetria ({src_alt.crs.to_string()}) não é projetado. Por favor, forneça um raster com CRS projetado.")
        alt_data = src_alt.read(1)
        alt_transform = src_alt.transform
        alt_crs = src_alt.crs
        alt_res = src_alt.res

    if target_resolution is None:
        target_resolution = uso_res

    if alt_res != target_resolution:
        with rasterio.open(alt_path) as src:
            new_height = int(src.height * src.res[0] / target_resolution[0])
            new_width = int(src.width * src.res[1] / target_resolution[1])

            alt_data = src.read(
                out_shape=(1, new_height, new_width),
                resampling=Resampling.bilinear
            )[0]
            alt_transform = src.transform * src.transform.scale(
                (src.width / new_width), (src.height / new_height)
            )

    min_rows = min(uso_data.shape[0], alt_data.shape[0])
    min_cols = min(uso_data.shape[1], alt_data.shape[1])

    uso_data = uso_data[:min_rows, :min_cols]
    alt_data = alt_data[:min_rows, :min_cols]

    return uso_data, alt_data, target_resolution, uso_crs, uso_transform
