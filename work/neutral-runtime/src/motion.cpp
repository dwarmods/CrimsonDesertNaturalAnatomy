#include "motion.h"
#include <algorithm>
#include <stdexcept>
namespace neutral {
namespace {
double bounded(double x,double low,double high){return std::clamp(x,low,high);}
Vec3 nearest(Vec3 point,const Capsule& c){Vec3 d=c.b-c.a;double n=dot(d,d);return c.a+d*(n>1e-18?bounded(dot(point-c.a,d)/n,0,1):0);}
}
Motion::Motion(std::vector<Node> nodes,Settings s):nodes_(std::move(nodes)),settings_(s){
 if(nodes_.empty()||nodes_.size()>64)throw std::invalid_argument("unsupported control-chain size");
 if(!std::isfinite(s.frequency_hz)||s.frequency_hz<.1||s.frequency_hz>20||!std::isfinite(s.damping_ratio)||s.damping_ratio<0||s.damping_ratio>3||!std::isfinite(s.gravity_scale)||s.gravity_scale<0||s.gravity_scale>2||!std::isfinite(s.maximum_offset)||s.maximum_offset<=0||s.maximum_offset>.1||s.solver_iterations<1||s.solver_iterations>64)throw std::invalid_argument("invalid motion settings");
 lengths_.resize(nodes_.size());
 for(size_t i=0;i<nodes_.size();++i){auto& n=nodes_[i];if(!finite(n.rest)||n.parent>=int(i)||n.parent< -1||!std::isfinite(n.radius)||n.radius<0)throw std::invalid_argument("invalid node hierarchy");if(n.parent>=0){lengths_[i]=length(n.rest-nodes_[n.parent].rest);if(lengths_[i]<1e-6)throw std::invalid_argument("zero-length segment");}else if(!n.fixed)throw std::invalid_argument("root must be fixed");}
 positions_.resize(nodes_.size());previous_=positions_;velocity_=positions_;
}
std::vector<Vec3> Motion::rest_positions(const Frame& f)const{std::vector<Vec3> r;for(auto& n:nodes_)r.push_back(f.position+f.rotation.apply(n.rest));return r;}
void Motion::reset(const Frame& f){positions_=rest_positions(f);previous_=positions_;velocity_.assign(nodes_.size(),{});previous_frame_=f;accumulated_=0;initialized_=true;active_=false;}
void Motion::update(double seconds,const Frame& f,Visibility visibility,const std::vector<Capsule>& colliders){
 if(!finite(f.position))return;
 if(!initialized_){reset(f);}
 if(visibility!=Visibility::Nude||!std::isfinite(seconds)||seconds<=0||seconds>.25||length(f.position-previous_frame_.position)>settings_.teleport_distance){reset(f);return;}
 for(auto& c:colliders)if(!finite(c.a)||!finite(c.b)||!std::isfinite(c.radius)||c.radius<0)throw std::invalid_argument("invalid collider");
 // Fixed simulation timestep bounds integration independently of presentation rate.
 constexpr double dt=1.0/240.0;accumulated_+=seconds;
 const Frame old=previous_frame_;const double elapsed=accumulated_;double consumed=0;
 while(accumulated_+1e-12>=dt){consumed+=dt;Frame interpolated=f;interpolated.position=old.position+(f.position-old.position)*bounded(consumed/elapsed,0,1);step(dt,interpolated,colliders);accumulated_-=dt;}
 previous_frame_=f;active_=true;
}
void Motion::step(double dt,const Frame& f,const std::vector<Capsule>& colliders){
 const auto rest=rest_positions(f);previous_=positions_;const double omega=2*3.141592653589793*settings_.frequency_hz;const double decay=std::exp(-2*settings_.damping_ratio*omega*dt);
 for(size_t i=0;i<nodes_.size();++i){
  if(nodes_[i].fixed){positions_[i]=rest[i];velocity_[i]={};continue;}
  const Vec3 acceleration=(rest[i]-positions_[i])*(omega*omega)+Vec3{0,-9.81*settings_.gravity_scale,0};
  velocity_[i]=(velocity_[i]+acceleration*dt)*decay;positions_[i]+=velocity_[i]*dt;
 }
 for(int iteration=0;iteration<settings_.solver_iterations;++iteration){
  for(size_t i=0;i<nodes_.size();++i){
   if(nodes_[i].fixed){positions_[i]=rest[i];continue;}
   Vec3 offset=positions_[i]-rest[i];double dist=length(offset);if(dist>settings_.maximum_offset)positions_[i]=rest[i]+offset*(settings_.maximum_offset/dist);
   int parent=nodes_[i].parent;
   if(parent>=0){Vec3 delta=positions_[i]-positions_[parent];double n=length(delta);Vec3 direction=normalized(delta,normalized(rest[i]-rest[parent]));Vec3 correction=direction*(n-lengths_[i]);if(nodes_[parent].fixed)positions_[i]=positions_[parent]+direction*lengths_[i];else{positions_[i]=positions_[i]-correction*.5;positions_[parent]+=correction*.5;}}
   for(auto& c:colliders){Vec3 center=nearest(positions_[i],c),d=positions_[i]-center;double n=length(d),radius=c.radius+nodes_[i].radius;if(n<radius)positions_[i]=center+normalized(d,normalized(rest[i]-center,{1,0,0}))*radius;}
  }
 }
 for(size_t i=0;i<nodes_.size();++i){velocity_[i]=(positions_[i]-previous_[i])/dt;if(!finite(positions_[i])||!finite(velocity_[i])){reset(f);return;}}
}
double Motion::worst_length_error()const{double error=0;for(size_t i=0;i<nodes_.size();++i)if(nodes_[i].parent>=0)error=std::max(error,std::abs(length(positions_[i]-positions_[nodes_[i].parent])-lengths_[i]));return error;}
}
