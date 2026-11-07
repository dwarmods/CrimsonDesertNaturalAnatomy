#include "fitting.h"
#include <algorithm>
#include <numeric>
#include <stdexcept>
#include <unordered_set>

namespace neutral {
const std::array<ControlSpec, control_count>& control_specs() {
    static const std::array<ControlSpec, control_count> specs{{
        {"anatomy_height","Anatomy height (mm)",-30,30,0},
        {"attachment_contour","Attachment contour (mm)",-8,8,0},
        {"attachment_smoothness","Attachment smoothing",0,1,0},
        {"shaft_base_width","Base width",.6,1.5,1},
        {"shaft_mid_width","Middle width",.6,1.5,1},
        {"shaft_tip_width","Tip width",.6,1.5,1},
        {"length","Length",.75,1.35,1},
        {"testicle_size","Testicle size",.7,1.4,1},
        {"hang","Hang (mm)",-10,35,0},
        {"separation","Separation (mm)",-5,15,0},
        {"z","Pelvis height (mm)",-40,40,0},
        {"scale","Overall size",.75,1.4,1},
        {"width","Overall width",.75,1.3,1},
        {"depth","Overall depth",.75,1.3,1},
        {"x","Horizontal position (mm)",-25,25,0},
        {"y","Depth position (mm)",-25,25,0}
    }};
    return specs;
}
Parameters default_parameters() {
    Parameters p{};
    for (unsigned i=0;i<control_count;++i) p[i]=control_specs()[i].initial;
    return p;
}
bool valid_parameters(const Parameters& p) {
    for (unsigned i=0;i<control_count;++i) {
        const auto& s=control_specs()[i];
        if (!std::isfinite(p[i]) || p[i]<s.minimum || p[i]>s.maximum) return false;
    }
    return true;
}
static double get(const Parameters& p, Control c) { return p[static_cast<unsigned>(c)]; }
double width_profile(double t, const Parameters& p) {
    const bool first=t<.5;
    const double x=first?t*2:(t-.5)*2, f=x*x*(3-2*x);
    return first?get(p,Control::BaseWidth)*(1-f)+get(p,Control::MidWidth)*f:
        get(p,Control::MidWidth)*(1-f)+get(p,Control::TipWidth)*f;
}
static void require(bool good, const char* reason) { if (!good) throw std::invalid_argument(reason); }
static bool unit(double v) { return std::isfinite(v) && v>=0 && v<=1; }
Fitter::Fitter(FitMesh mesh):mesh_(std::move(mesh)) {
    const auto& m=mesh_; const auto n=m.base.size();
    require(n>0 && n<=65535,"unsupported vertex count");
    require(finite(m.pivot) && finite(m.left_center) && finite(m.right_center),"invalid fit centers");
    require(m.seam_normals.size()==n,"normal count mismatch");
    for (auto v:m.base) require(finite(v),"nonfinite base position");
    for (auto v:m.seam_normals) require(finite(v),"nonfinite seam normal");
    for (const auto& field:m.fields) {
        require(field.size()==n,"weight field count mismatch");
        for (double v:field) require(unit(v),"weight field outside [0,1]");
    }
    require(m.relaxation.size()<=n && m.loft.size()<=n && m.metric.size()<=n,"patch too large");
    std::unordered_set<unsigned> seen;
    auto neighbors=[&](const std::vector<WeightedNeighbor>& ns, bool normalized) {
        require(!ns.empty() && ns.size()<=128,"invalid neighbor count");
        double total=0; std::unordered_set<unsigned> unique;
        for (auto v:ns) {
            require(v.vertex<n && unique.insert(v.vertex).second,"invalid or duplicate neighbor");
            require(std::isfinite(v.coefficient) && v.coefficient>=0,"invalid edge coefficient");
            total+=v.coefficient;
        }
        require(std::isfinite(total) && total>0,"zero/overflow edge weights");
        if (normalized) require(std::abs(total-1)<1e-6,"relaxation coefficients not normalized");
    };
    for (const auto& r:m.relaxation) {
        require(r.vertex<n && seen.insert(r.vertex).second && unit(r.weight),"invalid relaxation row");
        neighbors(r.neighbors,true);
    }
    seen.clear();
    for (const auto& r:m.loft) {
        require(r.vertex<n && seen.insert(r.vertex).second && r.inner<n && r.outer_a<n && r.outer_b<n,
            "invalid loft vertex");
        require(unit(r.fraction) && unit(r.t) && r.neighbors.size()<=128,"invalid loft interpolation");
        for (auto j:r.neighbors) require(j<n,"invalid loft neighbor");
    }
    metric_local_.assign(n,-1);
    for (unsigned i=0;i<m.metric.size();++i) {
        const auto& r=m.metric[i];
        require(r.vertex<n && metric_local_[r.vertex]<0 && std::isfinite(r.mass) && r.mass>0,
            "invalid metric row");
        neighbors(r.neighbors,false);metric_local_[r.vertex]=static_cast<int>(i);
    }
    // CG requires symmetric interior edges. Boundary vertices remain fixed.
    for (unsigned i=0;i<m.metric.size();++i) for (auto e:m.metric[i].neighbors) {
        const int j=metric_local_[e.vertex]; if (j<0) continue;
        auto& ns=m.metric[j].neighbors;
        auto back=std::find_if(ns.begin(),ns.end(),[&](auto b){return b.vertex==m.metric[i].vertex;});
        require(back!=ns.end() && std::abs(back->coefficient-e.coefficient)<=1e-8*std::max(1.,e.coefficient),
            "asymmetric metric patch");
    }
}
std::vector<Vec3> Fitter::deform(const Parameters& p) const {
    require(valid_parameters(p),"fitting parameter outside supported range");
    const auto& m=mesh_; auto out=m.base;
    const double scale=get(p,Control::Scale);
    const Vec3 scales{scale*get(p,Control::Width),scale*get(p,Control::Depth),scale};
    const Vec3 offset{get(p,Control::X)/1000,get(p,Control::Y)/1000,get(p,Control::Z)/1000};
    for (unsigned i=0;i<out.size();++i) {
        const double l=m.fields[FitMesh::Left][i], r=m.fields[FitMesh::Right][i],
            b=std::min(1.,l+r), s=m.fields[FitMesh::Shaft][i];
        Vec3 v=m.base[i]+((m.base[i]-m.left_center)*l+(m.base[i]-m.right_center)*r)*(get(p,Control::TesticleSize)-1);
        v.x+=(m.base[i].x-m.pivot.x)*(width_profile(m.fields[FitMesh::ProfileT][i],p)-1)*m.fields[FitMesh::ProfileWeight][i];
        v.z+=s*(m.base[i].z-m.pivot.z)*(get(p,Control::Length)-1)-b*get(p,Control::Hang)/1000;
        v.y+=m.fields[FitMesh::Attachment][i]*get(p,Control::Contour)/1000-b*get(p,Control::Separation)/1000;
        const Vec3 d=v-m.pivot; const double w=m.fields[FitMesh::AnatomyScale][i];
        out[i]=v+Vec3{d.x*(scales.x-1),d.y*(scales.y-1),d.z*(scales.z-1)}*w+offset*m.fields[FitMesh::Weight][i];
    }
    for (auto& r:m.loft) {
        const Vec3 start=out[r.inner], end=out[r.outer_a]*(1-r.fraction)+out[r.outer_b]*r.fraction;
        const double dx=end.x-start.x,dz=end.z-start.z,radial=std::hypot(dx,dz),t=r.t;
        double sy=0,sr=0;
        for (unsigned j:r.neighbors) {
            sy+=start.y-out[j].y; sr+=((start.x-out[j].x)*dx+(start.z-out[j].z)*dz)/std::max(radial,1e-9);
        }
        const double slope=sr>1e-6?std::clamp(sy/sr,-1.5,1.5):0;
        const Vec3 normal=m.seam_normals[r.outer_a]*(1-r.fraction)+m.seam_normals[r.outer_b]*r.fraction;
        const double tangent=std::clamp(-(normal.x*dx+normal.z*dz)/std::max(.1,normal.y),-1.5*radial,1.5*radial);
        out[r.vertex]={start.x+dx*t,(2*t*t*t-3*t*t+1)*start.y+(t*t*t-2*t*t+t)*slope*radial+
            (-2*t*t*t+3*t*t)*end.y+(t*t*t-t*t)*tangent,start.z+dz*t};
    }
    const double smoothness=get(p,Control::Smoothness);
    auto original=out, current=out; std::vector<Vec3> deltas(m.relaxation.size());
    for (int pass=0;pass<100;++pass) {
        for (unsigned k=0;k<m.relaxation.size();++k) {
            const auto& r=m.relaxation[k]; Vec3 sum{};
            for (auto e:r.neighbors) sum+=current[e.vertex]*e.coefficient;
            deltas[k]=(sum-current[r.vertex])*(.4*r.weight);
        }
        for (unsigned k=0;k<m.relaxation.size();++k) current[m.relaxation[k].vertex]+=deltas[k];
    }
    for (const auto& r:m.relaxation) out[r.vertex]=original[r.vertex]+(current[r.vertex]-original[r.vertex])*(.55+.45*smoothness);
    const auto count=m.metric.size();
    if (count) {
        const double radius=.004+.005*smoothness;
        std::vector<double> mass(count),diagonal(count);
        for (unsigned i=0;i<count;++i) {
            mass[i]=m.metric[i].mass/(radius*radius);diagonal[i]=mass[i];
            for (auto e:m.metric[i].neighbors) diagonal[i]+=e.coefficient;
        }
        auto apply=[&](const std::vector<double>& v, std::vector<double>& product) {
            for (unsigned i=0;i<count;++i) {
                product[i]=diagonal[i]*v[i];
                for (auto e:m.metric[i].neighbors) if (metric_local_[e.vertex]>=0)
                    product[i]-=e.coefficient*v[metric_local_[e.vertex]];
            }
        };
        auto component=[](Vec3 v,int axis){return axis==0?v.x:axis==1?v.y:v.z;};
        std::vector<double> x(count),rhs(count),residual(count),z(count),direction(count),product(count);
        for (int axis=0;axis<3;++axis) {
            for (unsigned i=0;i<count;++i) {
                x[i]=component(out[m.metric[i].vertex],axis);rhs[i]=mass[i]*x[i];
                for (auto e:m.metric[i].neighbors) if (metric_local_[e.vertex]<0)
                    rhs[i]+=e.coefficient*component(out[e.vertex],axis);
            }
            apply(x,product);double rz=0;
            for (unsigned i=0;i<count;++i) {residual[i]=rhs[i]-product[i];z[i]=residual[i]/diagonal[i];direction[i]=z[i];rz+=residual[i]*z[i];}
            for (int pass=0;pass<160 && rz>=1e-22;++pass) {
                apply(direction,product);const double denom=std::inner_product(direction.begin(),direction.end(),product.begin(),0.);
                if (denom<=0) break;
                const double step=rz/denom;double next_rz=0;
                for (unsigned i=0;i<count;++i) {x[i]+=step*direction[i];residual[i]-=step*product[i];z[i]=residual[i]/diagonal[i];next_rz+=residual[i]*z[i];}
                for (unsigned i=0;i<count;++i) direction[i]=z[i]+(next_rz/rz)*direction[i];rz=next_rz;
            }
            for (unsigned i=0;i<count;++i) {
                auto& v=out[m.metric[i].vertex];if (axis==0) v.x=x[i];else if (axis==1) v.y=x[i];else v.z=x[i];
            }
        }
    }
    for (unsigned i=0;i<out.size();++i) {
        out[i].z+=m.fields[FitMesh::AnatomyHeight][i]*get(p,Control::Height)/1000;
        require(finite(out[i]),"nonfinite fitting result");
    }
    return out;
}
}
