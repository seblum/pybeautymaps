import cairo
import numpy as np
import overpy

from . import utils

class Beautymap:

    @classmethod
    def centered(cls, center_latlon, size):
        bbox = utils.bbox_from_centered(center_latlon, size)
        return cls(bbox)

    def __init__(self, bbox):
        self.bbox = bbox
        self.road_types = {
            'motorway',
            'trunk',
            'primary',
            'secondary',
            'tertiary',
            'residential',
            'living_street',
        }

        self.raw_overpass_data = self.get_overpass_data()

        self.road_data = [
            way.tags.get('highway', '')
            for way in self.raw_overpass_data
        ]

        self.geodetic_data = [
            np.array([(node.lat, node.lon) for node in way.nodes], dtype=float)
            for way in self.raw_overpass_data
        ]

        self.cathographic_data = utils.cathographic_from_geodetic(*self.geodetic_data)


    def get_overpass_data(self):
        self.overpass_ql_query = f"""
            (
            way
                // filter road types with OR regex
                ["highway"~"^{'|'.join(self.road_types)}$"]
                {str(self.bbox)};
                >;
            );
            out;
        """
        return overpy.Overpass().query(self.overpass_ql_query).ways


    def render_square_png(self, filename, size, padding, line_widths=dict()):
        # 2D float
        coord_min = np.min([way.min(axis=0) for way in self.cathographic_data], axis=0)
        coord_max = np.max([way.max(axis=0) for way in self.cathographic_data], axis=0)
        coord_range = coord_max - coord_min

        scale = size / coord_range.min()

        with cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size) as surface:
            ctx = cairo.Context(surface)
            ctx.scale(1, 1)

            # white background
            ctx.rectangle(0, 0, size, size)
            ctx.set_source_rgb(1, 1, 1)
            ctx.fill()

            ctx.set_source_rgb(0, 0, 0)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            for way, road_type in zip(self.cathographic_data, self.road_data):
                ctx.set_line_width(line_widths.get(road_type, 1))
                way_zeroed = np.rint((way - coord_min) * scale).astype(int)
                x, y = way_zeroed[0, :]
                ctx.move_to(x, size - y)
                for x, y in way_zeroed[1:]:
                    ctx.line_to(x, size - y)
                ctx.stroke()

            # padding
            ctx.set_source_rgb(1, 1, 1)
            padding_rects = [
                (0, 0, size, padding),
                (0, 0, padding, size),
                (size - padding, 0, padding, size),
                (0, size - padding, size, padding),
            ]
            for rect in padding_rects:
                ctx.rectangle(*rect)
                ctx.fill()

            surface.write_to_png(filename)