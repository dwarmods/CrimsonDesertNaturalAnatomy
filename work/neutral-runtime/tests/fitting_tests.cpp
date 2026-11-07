#include "fitting.h"
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <fstream>
#include <limits>
#include <stdexcept>
using namespace neutral;
static void require(bool good,const char* why) {if (!good) throw std::runtime_error(why);}
static FitMesh simple() {
    FitMesh m;m.base={{0,0,0},{.01,.01,-.04},{-.01,-.01,-.03},{.01,-.01,-.03}};
    m.seam_normals.assign(4,{0,1,0});
    for (auto& f:m.fields) f.assign(4,0);
    m.left_center=m.base[2];m.right_center=m.base[3];
    m.fields[FitMesh::Shaft][1]=1;m.fields[FitMesh::ProfileWeight][1]=1;
    m.fields[FitMesh::ProfileT][1]=.5;m.fields[FitMesh::Left][2]=1;m.fields[FitMesh::Right][3]=1;
    for (int i=1;i<4;++i) {m.fields[FitMesh::Weight][i]=1;m.fields[FitMesh::AnatomyHeight][i]=1;m.fields[FitMesh::AnatomyScale][i]=1;}
    return m;
}
int main(int argc,char** argv) {try {
    auto p=default_parameters();Fitter fitter(simple());auto baseline=fitter.deform(p);
    require(length(baseline[1]-fitter.mesh().base[1])<1e-12,"neutral shape changed");
    p[static_cast<unsigned>(Control::Length)]=1.25;auto length_fit=fitter.deform(p);
    require(std::abs(length_fit[1].z+.05)<1e-12 && length(length_fit[2]-baseline[2])<1e-12,"length affected scrotal region");
    p=default_parameters();p[static_cast<unsigned>(Control::Height)]=10;auto moved=fitter.deform(p);
    require(length(moved[0]-baseline[0])==0 && std::abs(moved[1].z-baseline[1].z-.01)<1e-12,"relative height moved torso");
    p=default_parameters();p[static_cast<unsigned>(Control::Hang)]=20;p[static_cast<unsigned>(Control::Separation)]=10;auto hanging=fitter.deform(p);
    require(length(hanging[1]-baseline[1])==0 && std::abs(hanging[2].z-baseline[2].z+.02)<1e-12 &&
        std::abs(hanging[2].y-baseline[2].y+.01)<1e-12,"scrotal controls affected shaft");
    for (unsigned i=0;i<control_count;++i) {
        for (double v:{control_specs()[i].minimum,control_specs()[i].maximum}) {
            p=default_parameters();p[i]=v;for (auto x:fitter.deform(p)) require(finite(x),"nonfinite at control limit");
        }
        p=default_parameters();p[i]=std::numeric_limits<double>::quiet_NaN();require(!valid_parameters(p),"NaN accepted");
        p[i]=control_specs()[i].maximum+1;require(!valid_parameters(p),"out of range accepted");
    }
    auto bad=simple();bad.relaxation.push_back({1,1,{{500,1}}});bool rejected=false;
    try {Fitter f(std::move(bad));} catch (const std::invalid_argument&) {rejected=true;}
    require(rejected,"invalid topology accepted");
    // Optional local mesh fixtures are never distributed with the sources.
    if (argc>1) {
        const std::filesystem::path dir=argv[1];Fitter full(load_fit_mesh(dir/"body.nafit"));
        std::ifstream reference(dir/"reference.bin",std::ios::binary);
        auto read=[&](void* out,size_t bytes) {require(bool(reference.read(static_cast<char*>(out),bytes)),"truncated parity reference");};
        std::uint32_t cases{},n{};read(&cases,4);read(&n,4);
        require(cases>0 && cases<100 && n==full.mesh().base.size(),"wrong reference dimensions");
        double worst=0, milliseconds=0;
        for (unsigned c=0;c<cases;++c) {
            read(p.data(),sizeof(double)*p.size());std::vector<Vec3> wanted(n);read(wanted.data(),sizeof(Vec3)*n);
            const auto start=std::chrono::steady_clock::now();auto actual=full.deform(p);
            milliseconds+=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();
            for (unsigned i=0;i<n;++i) worst=std::max(worst,length(actual[i]-wanted[i]));
        }
        require(worst<2e-6,"native fitting diverges from Python reference");
        std::printf("PASS: %u local parity cases, %u vertices, max error %.9g m, mean solve %.3f ms\n",cases,n,worst,milliseconds/cases);
        // Parser must reject an incomplete file before trusting any arrays.
        std::ofstream truncated(dir/"truncated.nafit",std::ios::binary);truncated.write("NAFIT01!",8);truncated.close();
        rejected=false;try {load_fit_mesh(dir/"truncated.nafit");}catch (const std::runtime_error&) {rejected=true;}
        require(rejected,"truncated fitting asset accepted");
    }
    std::puts("PASS: fitting control bounds, neutral shape, regional isolation, relative placement and malformed topology rejection.");
    return 0;
}catch(const std::exception& e) {std::fprintf(stderr,"FAIL: %s\n",e.what());return 1;}}
