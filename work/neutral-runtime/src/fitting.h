#pragma once
#include "motion.h"
#include <filesystem>
#include <string>

namespace neutral {
enum class Control : unsigned { Height, Contour, Smoothness, BaseWidth, MidWidth,
    TipWidth, Length, TesticleSize, Hang, Separation, Z, Scale, Width, Depth, X, Y, Count };
constexpr unsigned control_count = static_cast<unsigned>(Control::Count);
struct ControlSpec { const char* key; const char* label; double minimum, maximum, initial; };
const std::array<ControlSpec, control_count>& control_specs();
using Parameters = std::array<double, control_count>;
Parameters default_parameters();
bool valid_parameters(const Parameters& parameters);
double width_profile(double t, const Parameters& parameters);

struct WeightedNeighbor { unsigned vertex; double coefficient; };
struct RelaxRow { unsigned vertex; double weight; std::vector<WeightedNeighbor> neighbors; };
struct LoftRow { unsigned vertex, inner, outer_a, outer_b; double fraction, t; std::vector<unsigned> neighbors; };
struct MetricRow { unsigned vertex; double mass; std::vector<WeightedNeighbor> neighbors; };
struct FitMesh {
    // Editor coordinates: metres, Z up. Convert only at a verified native binding.
    std::vector<Vec3> base, seam_normals;
    Vec3 pivot, left_center, right_center;
    enum Field { Weight, Left, Right, Shaft, ProfileT, ProfileWeight, Attachment, AnatomyScale, AnatomyHeight, Fields };
    std::array<std::vector<double>, Fields> fields;
    std::vector<RelaxRow> relaxation;
    std::vector<LoftRow> loft;
    std::vector<MetricRow> metric;
};
FitMesh load_fit_mesh(const std::filesystem::path& path);
class Fitter {
public:
    explicit Fitter(FitMesh mesh);
    std::vector<Vec3> deform(const Parameters& parameters) const;
    const FitMesh& mesh() const { return mesh_; }
private:
    FitMesh mesh_;
    std::vector<int> metric_local_;
};
}
