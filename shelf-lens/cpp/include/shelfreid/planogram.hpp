// The planogram of a shelf map: its bottles in shelves, each shelf left to right, with sizes
// and gaps in bottle units. The map keeps the perspective of keyframe 0 (and some drift), so
// only local geometry is used:
//  - a bottle's right neighbour is the one the frames saw there most (Tracker::right), else
//    the nearest bottle to its right along its own bottom edge, about as low;
//  - the rows these links make join across gaps when one ends where the other starts;
//  - positions along the shelves are a least-squares fit of the in-frame offsets of bottle
//    pairs seen together (a shelf above or below included), in units of a frame's median
//    bottle height. Bottles no frame links take the map's local sizes and gaps instead.
// Provisional bottles (`skip`) and duplicates on the map (the one seen less goes) are left out.
#pragma once

#include <set>
#include <string>
#include <vector>

#include "shelfreid/tracker.hpp"

namespace shelfreid {

struct Facing {
    int bottle = 0;
    double x = 0, width = 0, height = 0;   // bottle units: the left edge, the size
};

struct Shelf {
    std::vector<Facing> facings;   // left to right; x from the leftmost facing of all shelves
    double width = 0;              // bottle units: the right edge of its last facing
};

struct Planogram {
    std::vector<Shelf> shelves;    // the bottom one first (shelf 1)
    std::vector<int> duplicates;   // bottles left out as duplicates of others
};

// `offsets`, `shapes` (Tracker): where the frames saw the bottles from each other and their
// sizes; the layout comes from them where they link the bottles, else from the map.
Planogram planogram(const std::vector<Placed>& bottles, const std::map<int, std::map<int, int>>& right,
                    const std::set<int>& skip = {}, double aspect = 0.3,
                    const std::map<std::pair<int, int>, Offset>* offsets = nullptr,
                    const std::map<int, Shape>* shapes = nullptr);
// The planogram of a tracker's map, `aspect` from its running bottle size (0.3 before it
// has one); `skip`: a RealtimeTracker's provisional bottles.
Planogram planogram(const Tracker& tracker, const std::set<int>& skip = {});

// {"shelves": [{"width": W, "facings": [{"bottle": id, "x": x, "width": w, "height": h}, ...]}, ...],
//  "duplicates": [...]}, the bottom shelf first.
std::string to_json(const Planogram& planogram);

}  // namespace shelfreid
