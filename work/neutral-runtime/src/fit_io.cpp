#include "fitting.h"
#include <cstring>
#include <fstream>
#include <stdexcept>

namespace neutral {
namespace {
class Reader {
public:
    explicit Reader(const std::filesystem::path& path) {
        std::ifstream in(path,std::ios::binary|std::ios::ate);
        if (!in) throw std::runtime_error("cannot open fitting asset");
        const auto size=in.tellg();
        if (size<12 || size>64*1024*1024) throw std::runtime_error("unsupported fitting asset size");
        data.resize(static_cast<size_t>(size));in.seekg(0);
        if (!in.read(data.data(),size)) throw std::runtime_error("cannot read fitting asset");
        if (std::memcmp(data.data(),"NAFIT01!",8)) throw std::runtime_error("unknown fitting asset version");
        at=8;
    }
    template<class T> T scalar() {
        if (sizeof(T)>data.size()-at) throw std::runtime_error("truncated fitting asset");
        T value{};std::memcpy(&value,data.data()+at,sizeof(T));at+=sizeof(T);return value;
    }
    unsigned count(unsigned maximum) {
        const auto n=scalar<std::uint32_t>();
        if (n>maximum) throw std::runtime_error("fitting asset count exceeds limit");
        return n;
    }
    Vec3 vec() {return {scalar<double>(),scalar<double>(),scalar<double>()};}
    std::vector<WeightedNeighbor> edges() {
        const auto n=count(128);edge_count+=n;
        if (edge_count>2000000) throw std::runtime_error("too many fitting edges");
        std::vector<WeightedNeighbor> ns;
        for (unsigned i=0;i<n;++i) ns.push_back({scalar<std::uint32_t>(),scalar<double>()});
        return ns;
    }
    void finish() {if (at!=data.size()) throw std::runtime_error("unexpected fitting asset suffix");}
private:
    std::vector<char> data;size_t at{},edge_count{};
};
}
FitMesh load_fit_mesh(const std::filesystem::path& path) {
    // NAFIT01 is little-endian, with IEEE binary64 values; supported host: x64.
    Reader in(path);FitMesh m;const auto n=in.count(65535);
    for (unsigned i=0;i<n;++i) m.base.push_back(in.vec());
    m.pivot=in.vec();m.left_center=in.vec();m.right_center=in.vec();
    for (auto& field:m.fields) for (unsigned i=0;i<n;++i) field.push_back(in.scalar<double>());
    for (unsigned i=0;i<n;++i) m.seam_normals.push_back(in.vec());
    auto count=in.count(n);
    for (unsigned i=0;i<count;++i) {
        RelaxRow row{};row.vertex=in.scalar<std::uint32_t>();row.weight=in.scalar<double>();row.neighbors=in.edges();
        m.relaxation.push_back(std::move(row));
    }
    count=in.count(n);
    for (unsigned i=0;i<count;++i) {
        LoftRow r{};r.vertex=in.scalar<std::uint32_t>();r.inner=in.scalar<std::uint32_t>();
        r.outer_a=in.scalar<std::uint32_t>();r.outer_b=in.scalar<std::uint32_t>();
        r.fraction=in.scalar<double>();r.t=in.scalar<double>();
        const auto edges=in.count(128);
        for (unsigned j=0;j<edges;++j) r.neighbors.push_back(in.scalar<std::uint32_t>());
        m.loft.push_back(std::move(r));
    }
    count=in.count(n);
    for (unsigned i=0;i<count;++i) {
        MetricRow r{};r.vertex=in.scalar<std::uint32_t>();r.mass=in.scalar<double>();r.neighbors=in.edges();
        m.metric.push_back(std::move(r));
    }
    in.finish();return m; // Fitter performs semantic validation before any deformation.
}
}
