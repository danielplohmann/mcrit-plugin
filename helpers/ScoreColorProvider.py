import math

class ScoreColorProvider(object):
    
    frequency_color_map = {
        # white
        0 : (0xff, 0xff, 0xff),
        # blue
        1: (0x10, 0x7f, 0xfc),
        # light blue
        2: (0x22, 0xfe, 0xfd),
        # green
        3: (0x1f, 0xfe, 0x28),
        # green yellow: (0xc1, 0xfe, 0x2f)
        # yellow
        4: (0xff, 0xff, 0x35),
        # light orange: (0xfe, 0xc1, 0x2c)
        # orange
        5: (0xfe, 0x82, 0x25),
        # light red:
        #6: (0xfd, 0x46, 0x21),
        # red
        6: (0xfd, 0x1a, 0x20),
        # violet
        7: (0xb4, 0x00, 0xff)
    }

    matching_color_map_50 = {
        # white
        0: (0xff, 0xff, 0xff),
        # dark blue
        1: (0x00, 0x45, 0xba),
        # blue
        2: (0x00, 0x80, 0xff),
        # light blue
        3: (0x22, 0xfe, 0xfd),
        # green
        4: (0x1f, 0xfe, 0x28),
        # yellow
        5: (0xff, 0xff, 0x35),
        # orange
        6: (0xfe, 0x82, 0x25),
        # red
        7: (0xfd, 0x1a, 0x20),
    }

    def _calculateLogScore(self, cluster_size):
        if cluster_size == 0:
            return 0
        elif cluster_size == 1:
            return 1
        else:
            return 1 + int(math.log(cluster_size, 2))

    def _adjustOpacity(self, tup, opacity=1):
        return tuple(int(255 - opacity * (255 - e)) for e in tup)

    def frequencyToColor(self, count, opacity=1):
        top_color_tuple = self._adjustOpacity(self.frequency_color_map[max(self.frequency_color_map)], opacity)
        frequency = self._calculateLogScore(count)
        if frequency in self.frequency_color_map:
            top_color_tuple = self._adjustOpacity(self.frequency_color_map[frequency], opacity)
        return top_color_tuple

    def scoreToColor(self, score, opacity=1):
        if score > 100:
            return self._adjustOpacity(self.matching_color_map_50[1], opacity)
        elif score == 100:
            return self._adjustOpacity(self.matching_color_map_50[2], opacity)
        elif score >= 90:
            return self._adjustOpacity(self.matching_color_map_50[3], opacity)
        elif score >= 80:
            return self._adjustOpacity(self.matching_color_map_50[4], opacity)
        elif score >= 70:
            return self._adjustOpacity(self.matching_color_map_50[5], opacity)
        elif score >= 60:
            return self._adjustOpacity(self.matching_color_map_50[6], opacity)
        elif score >= 50:
            return self._adjustOpacity(self.matching_color_map_50[7], opacity)
        return self._adjustOpacity(self.frequency_color_map[0])

    def uniqueScoreToColor(self, score, opacity=0.4):
        if score is not None and score > 0:
            return self.scoreToColor(60, opacity=opacity)
        return self._adjustOpacity(self.frequency_color_map[0], opacity=1)

    def __init__(self) -> None:
        pass
