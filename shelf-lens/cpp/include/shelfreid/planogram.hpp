// The planogram of a shelf map: its bottles in shelves, each shelf left to right, with the
// sizes and the gaps in bottle units. The map is a homography of keyframe 0, so it keeps the
// perspective of that frame (and some drift): rows fan out and bottles grow across it. Only
// local geometry is used, so that cancels out:
//  - a bottle's right neighbour is the one the frames saw there most (Tracker::right), or
//    else the nearest bottle to its right along its own bottom edge, about as low;
//  - the rows these links make join across gaps (an empty place, a bottle not met) when
//    one ends where the other starts, about as low;
//  - where a bottle stands along the shelves comes from the frames: the offsets of the
//    pairs of bottles seen together (a shelf above or below included), fitted by least
//    squares, so the shelves line up with each other; sizes are in units of a frame's
//    median bottle height. Without them (or for bottles no frame links to the rest), from
//    the map: a height in units of the median height of the bottles around, a width or a
//    gap in units of their median width, times `aspect`.
// A bottle a frame never saw alone (provisional) or one that covers most of another (a
// duplicate of the map: the one with fewer sightings goes) is left out.
#pragma once

#include <set>
#include <string>
#include <vector>

#include "shelfreid/tracker.hpp"

namespace shelfreid {

struct Facing {
    int bottle = 0;
    double x = 0, width = 0, height = 0;   // bottle units: the left edge from the shelf's start, the size
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
