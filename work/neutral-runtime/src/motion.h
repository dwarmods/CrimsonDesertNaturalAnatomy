#pragma once
#include <array>
#include <cmath>
#include <cstdint>
#include <vector>

namespace neutral {
struct Vec3 {
 double x{},y{},z{};
 Vec3 operator+(Vec3 b)const{return {x+b.x,y+b.y,z+b.z};}
 Vec3 operator-(Vec3 b)const{return {x-b.x,y-b.y,z-b.z};}
 Vec3 operator*(double s)const{return {x*s,y*s,z*s};}
 Vec3 operator/(double s)const{return *this*(1/s);}
 Vec3& operator+=(Vec3 b){return *this=*this+b;}
};
inline double dot(Vec3 a,Vec3 b){return a.x*b.x+a.y*b.y+a.z*b.z;}
inline double length(Vec3 a){return std::sqrt(dot(a,a));}
inline bool finite(Vec3 a){return std::isfinite(a.x)&&std::isfinite(a.y)&&std::isfinite(a.z);}
inline Vec3 normalized(Vec3 a,Vec3 fallback={0,-1,0}){double n=length(a);return n>1e-12?a/n:fallback;}
struct Mat3 {
 std::array<Vec3,3> columns{{{1,0,0},{0,1,0},{0,0,1}}};
 Vec3 apply(Vec3 v)const{return columns[0]*v.x+columns[1]*v.y+columns[2]*v.z;}
};
struct Frame {Vec3 position{};Mat3 rotation{};};
struct Node {Vec3 rest{};int parent{-1};double radius{.008};bool fixed{};};
struct Capsule {Vec3 a{},b{};double radius{};};
struct Settings {
 double frequency_hz{5.0},damping_ratio{.85},gravity_scale{1.0};
 double maximum_offset{.025},teleport_distance{.5};
 int solver_iterations{12};
};
enum class Visibility { Unknown,Clothed,Nude };
class Motion {
public:
 explicit Motion(std::vector<Node> nodes,Settings settings={});
 void reset(const Frame& frame);
 void update(double seconds,const Frame& frame,Visibility visibility,const std::vector<Capsule>& colliders={});
 const std::vector<Vec3>& positions()const{return positions_;}
 std::vector<Vec3> rest_positions(const Frame& frame)const;
 bool active()const{return active_;}
 double worst_length_error()const;
private:
 void step(double dt,const Frame& frame,const std::vector<Capsule>& colliders);
 std::vector<Node> nodes_;
 std::vector<Vec3> positions_,previous_,velocity_;
 std::vector<double> lengths_;
 Settings settings_;Frame previous_frame_{};
 double accumulated_{};bool initialized_{},active_{};
};
}
