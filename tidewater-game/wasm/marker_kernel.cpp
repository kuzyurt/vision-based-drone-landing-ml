// FP64 acceleration of the frozen v5 marker registration's hot loops.
// The FP64 TRF port retains the reference loss, bounds, finite differences,
// iteration limits and acceptance tests. No pixel/sample is dropped.
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <limits>
#include <vector>
#include "marker_trf.h"

namespace {
constexpr int W=640,H=360,N=W*H,MAX_Q=240,SEGMENTS=20,SAMPLES=180;
using Point=std::array<double,2>;
std::array<uint8_t,N> mask{},predicted{};
std::array<Point,MAX_Q> observed{};
std::vector<int> nearestOrder;
std::vector<Point> nearestObserved;
std::array<std::array<Point,2>,SEGMENTS> edges{};
std::array<Point,SAMPLES> samples{};
std::array<double,28> parameters{};
std::array<double,6> info{};
std::array<double,MAX_Q+SAMPLES> output{},temporary{},baseline{};
std::array<double,(MAX_Q+SAMPLES)*4> jacobian{};
std::array<double,13> finishResult{};
std::array<double,5+(MAX_Q+SAMPLES)*4> fitResult{};
std::vector<uint32_t> paintPixels;
int count=0,paintCount=0;
double radius=0,lower=0,upper=0;
std::array<double,3> cameraNormal{},cameraX{},cameraY{};
double clamp(double x,double a,double b){return std::max(a,std::min(b,x));}
void buildNearest(int lo,int hi,int depth=0){
 if(lo>=hi)return;const int mid=(lo+hi)/2,axis=depth%2;
 std::nth_element(nearestOrder.begin()+lo,nearestOrder.begin()+mid,nearestOrder.begin()+hi,[axis](int a,int b){return nearestObserved[a][axis]<nearestObserved[b][axis];});
 buildNearest(lo,mid,depth+1);buildNearest(mid+1,hi,depth+1);
}
void nearestSquared(const Point&q,double&best,int lo,int hi,int depth=0){
 if(lo>=hi)return;const int mid=(lo+hi)/2,axis=depth%2;const Point&p=nearestObserved[nearestOrder[mid]];
 const double dx=q[0]-p[0],dy=q[1]-p[1],delta=q[axis]-p[axis];best=std::min(best,dx*dx+dy*dy);
 if(delta<0){nearestSquared(q,best,lo,mid,depth+1);if(delta*delta<best)nearestSquared(q,best,mid+1,hi,depth+1);}
 else {nearestSquared(q,best,mid+1,hi,depth+1);if(delta*delta<best)nearestSquared(q,best,lo,mid,depth+1);}
}
double dot(const double* a,const double* b){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
bool rayCoordinates(double px,double py,Point& q){
 const double cam[3]={(px-320)/parameters[21],-(py-180)/parameters[21],-1};
 const double denom=dot(cameraNormal.data(),cam);if(denom>=-.05)return false;
 q={dot(cameraX.data(),cam)/denom,dot(cameraY.data(),cam)/denom};return true;
}
void initializeTemplate(){
 int i=0;
 for(double half:{.13,.123}){const Point c[5]={{{-half,-half}},{{half,-half}},{{half,half}},{{-half,half}},{{-half,-half}}};for(int j=0;j<4;j++)edges[i++]={c[j],c[j+1]};}
 const double a=.085,b=.005;const Point p[13]={{{-b,-a}},{{b,-a}},{{b,-b}},{{a,-b}},{{a,b}},{{b,b}},{{b,a}},{{-b,a}},{{-b,b}},{{-a,b}},{{-a,-b}},{{-b,-b}},{{-b,-a}}};
 for(int j=0;j<12;j++)edges[i++]={p[j],p[j+1]};
 for(int j=0;j<SEGMENTS;j++)for(int k=0;k<9;k++){const double t=k/8.;samples[j*9+k]={edges[j][0][0]+t*(edges[j][1][0]-edges[j][0][0]),edges[j][0][1]+t*(edges[j][1][1]-edges[j][0][1])};}
}
int reflect(int x,int n){while(x<0||x>=n){if(x<0)x=-x-1;if(x>=n)x=2*n-x-1;}return x;}
void coldCenter(){
 const double f=parameters[21],distance=parameters[22],sigma=clamp(f*.065/distance,2,30),search=clamp(f*.12/distance+8,16,70);
 const int support=int(4*sigma+.5),y0=std::max(0,int(std::floor(parameters[26]-search))+1),y1=std::min(H-1,int(std::ceil(parameters[26]+search))-1),
  x0=std::max(0,int(std::floor(parameters[25]-search))+1),x1=std::min(W-1,int(std::ceil(parameters[25]+search))-1);
 if(x0>x1||y0>y1)return;
 std::vector<double> weights(2*support+1);double sum=0;
 for(int k=-support;k<=support;k++){weights[k+support]=std::exp(-.5/(sigma*sigma)*(k*k));sum+=weights[k+support];}
 for(double& x:weights)x/=sum;
 // Same separable Gaussian, restricted to the search and its exact support.
 // Pixels outside the search cannot affect the original argmax result.
 const int xa=std::max(0,x0-support),xb=std::min(W-1,x1+support),stride=xb-xa+1;
 std::vector<double> vertical((y1-y0+1)*stride);
 // Adjacent columns are independent. Keep each pixel's original FP64 sum
 // order while computing reflected row addresses once per row and weight.
 for(int y=y0;y<=y1;y++){
  double* row=vertical.data()+(y-y0)*stride;
  for(int x=xa;x<=xb;x++)row[x-xa]=weights[support]*mask[y*W+x];
  for(int k=1;k<=support;k++){
   const uint8_t* a=mask.data()+reflect(y-k,H)*W;const uint8_t* b=mask.data()+reflect(y+k,H)*W;
   const double weight=weights[support-k];
   for(int x=xa;x<=xb;x++)row[x-xa]+=weight*(a[x]+b[x]);
  }
 }
 double best=-1;int px=0,py=0;
 for(int y=y0;y<=y1;y++)for(int x=x0;x<=x1;x++){double value=weights[support]*vertical[(y-y0)*stride+x-xa];for(int k=1;k<=support;k++)value+=weights[support-k]*(vertical[(y-y0)*stride+reflect(x-k,W)-xa]+vertical[(y-y0)*stride+reflect(x+k,W)-xa]);if(value>best){best=value;px=x;py=y;}}
 if(best>.01){parameters[25]=px;parameters[26]=py;Point q;if(rayCoordinates(px,py,q)){parameters[23]=q[0];parameters[24]=q[1];}}
}
bool insideROI(int x,int y,double margin=0){return std::abs(x-parameters[25])<radius-margin&&std::abs(y-parameters[26])<radius-margin;}
bool templateInside(Point tq){
 double ray[3];for(int i=0;i<3;i++)ray[i]=parameters[9+i]+tq[0]*parameters[12+i]+tq[1]*parameters[15+i];
 double camera[3];for(int i=0;i<3;i++)camera[i]=parameters[i]*ray[0]+parameters[3+i]*ray[1]+parameters[6+i]*ray[2];
 const double x=320+parameters[21]*camera[0]/-camera[2],y=180-parameters[21]*camera[1]/-camera[2];
 return x>3&&x<637&&y>3&&y<357&&std::abs(x-parameters[25])<radius-3&&std::abs(y-parameters[26])<radius-3;
}
void residual(const double* v,double* out){
 const double distance=std::exp(v[2]),c=std::cos(v[3]),s=std::sin(v[3]),f=parameters[21];
 std::array<std::array<Point,2>,SEGMENTS> rotated;
 for(int j=0;j<SEGMENTS;j++)for(int k=0;k<2;k++)rotated[j][k]={c*edges[j][k][0]-s*edges[j][k][1],s*edges[j][k][0]+c*edges[j][k][1]};
 for(int i=0;i<count;i++){
  const double x=distance*(v[0]-observed[i][0]),y=distance*(v[1]-observed[i][1]);double nearest=std::numeric_limits<double>::infinity();
  for(const auto& edge:rotated){const double dx=edge[1][0]-edge[0][0],dy=edge[1][1]-edge[0][1],t=clamp(((x-edge[0][0])*dx+(y-edge[0][1])*dy)/(dx*dx+dy*dy),0,1),ex=x-(edge[0][0]+t*dx),ey=y-(edge[0][1]+t*dy);nearest=std::min(nearest,ex*ex+ey*ey);}
  out[i]=std::sqrt(nearest)/distance*f;
 }
 for(int i=0;i<SAMPLES;i++){
  const Point q={v[0]-(c*samples[i][0]-s*samples[i][1])/distance,v[1]-(s*samples[i][0]+c*samples[i][1])/distance};double nearest=std::numeric_limits<double>::infinity();
  if(templateInside(q)){nearestSquared(q,nearest,0,int(nearestObserved.size()));out[count+i]=std::sqrt(nearest)*f*.6;}
  else out[count+i]=0.;
 }
}
bool dilated(const std::array<uint8_t,N>& image,int x,int y){for(int dy=-2;dy<=2;dy++)for(int dx=-2;dx<=2;dx++)if(std::abs(dx)+std::abs(dy)<=2&&x+dx>=0&&x+dx<W&&y+dy>=0&&y+dy<H&&image[(y+dy)*W+x+dx])return true;return false;}
}
extern "C" {
const uint32_t* marker_paint(const uint8_t* rgb){
 paintPixels.clear();paintPixels.push_back(0);
 for(int i=0;i<N;i++){const int r=rgb[3*i],g=rgb[3*i+1],b=rgb[3*i+2];if(std::min(g,b)-r>45&&g>=b-12&&g>85)paintPixels.push_back(i);}
 paintPixels[0]=uint32_t(paintPixels.size()-1);return paintPixels.data();
}
int marker_begin(const uint8_t* rgb,const double* input){
 std::copy(input,input+28,parameters.begin());initializeTemplate();
 for(int i=0;i<3;i++){cameraNormal[i]=0;cameraX[i]=0;cameraY[i]=0;for(int k=0;k<3;k++){cameraNormal[i]+=parameters[3*k+i]*parameters[9+k];cameraX[i]+=parameters[3*k+i]*parameters[12+k];cameraY[i]+=parameters[3*k+i]*parameters[15+k];}}
 for(int i=0;i<N;i++){const int r=rgb[3*i],g=rgb[3*i+1],b=rgb[3*i+2];mask[i]=std::min(g,b)-r>45&&g>=b-12&&g>85;}
 if(!parameters[27])coldCenter();
 radius=clamp(parameters[21]*.20/parameters[22]+(parameters[27]?10:3),12,310);
 paintCount=0;for(int y=0;y<H;y++)for(int x=0;x<W;x++){mask[y*W+x]&=insideROI(x,y);paintCount+=mask[y*W+x];}if(paintCount<12)return 0;
 std::vector<Point> border;
 for(int y=3;y<357;y++)for(int x=3;x<637;x++)if(mask[y*W+x]&&insideROI(x,y,3)&&!(mask[(y-1)*W+x]&&mask[(y+1)*W+x]&&mask[y*W+x-1]&&mask[y*W+x+1]))border.push_back({double(x),double(y)});
 if(border.size()<12)return 0;
 const int selected=std::min(int(border.size()),MAX_Q);count=0;
 for(int i=0;i<selected;i++){const int index=i==selected-1?int(border.size())-1:int(i*(double(border.size()-1)/(selected-1)));Point q;if(rayCoordinates(border[index][0],border[index][1],q))observed[count++]=q;}
 if(count<12)return 0;
 // Keep the original representative forward residual samples. Reverse
 // template-to-observation distances use EVERY observed border pixel, avoiding
 // a scale-dependent distance floor from the sparse240-point forward subset.
 nearestObserved.clear();
 for(const Point& pixel:border){Point q;if(rayCoordinates(pixel[0],pixel[1],q))nearestObserved.push_back(q);}
 nearestOrder.resize(nearestObserved.size());
 for(int i=0;i<int(nearestObserved.size());i++)nearestOrder[i]=i;
 buildNearest(0,int(nearestObserved.size()));
 lower=std::max(.035,parameters[22]*.45);upper=std::min(12.,parameters[22]*1.55);
 info={parameters[25],parameters[26],parameters[23],parameters[24],double(count),double(paintCount)};return 1;
}
const double* marker_info(){return info.data();}
const double* marker_residual(const double* v){residual(v,output.data());return output.data();}
const double* marker_jacobian(const double* v){
 const double lo[4]={-50,-50,std::log(lower),-M_PI/4},hi[4]={50,50,std::log(upper),M_PI/4};residual(v,baseline.data());
 for(int j=0;j<4;j++){
  double h=1e-4*(v[j]>=0?1:-1)*std::abs(v[j]);if((v[j]+h)-v[j]==0)h=std::sqrt(std::numeric_limits<double>::epsilon())*(v[j]>=0?1:-1)*std::max(1.,std::abs(v[j]));
  const double ld=v[j]-lo[j],ud=hi[j]-v[j];if(v[j]+h<lo[j]||v[j]+h>hi[j]){if(std::abs(h)<=std::max(ld,ud))h=-h;else h=ud>=ld?ud:-ld;}
  double changed[4]={v[0],v[1],v[2],v[3]};changed[j]+=h;const double dx=changed[j]-v[j];residual(changed,temporary.data());
  for(int i=0;i<count+SAMPLES;i++)jacobian[i*4+j]=(temporary[i]-baseline[i])/dx;
 }
 return jacobian.data();
}
const double* marker_fit(const double* initial){
 const trf::V lo={-50,-50,std::log(lower),-M_PI/4},hi={50,50,std::log(upper),M_PI/4};
 trf::V x;std::copy(initial,initial+4,x.begin());
 auto fit=trf::solve(x,lo,hi,count+SAMPLES,[](const trf::V&v){residual(v.data(),output.data());return std::vector<double>(output.begin(),output.begin()+count+SAMPLES);},[](const trf::V&v){marker_jacobian(v.data());std::vector<trf::V> j(count+SAMPLES);for(int i=0;i<count+SAMPLES;i++)for(int k=0;k<4;k++)j[i][k]=jacobian[i*4+k];return j;});
 std::copy(fit.x.begin(),fit.x.end(),fitResult.begin());fitResult[4]=fit.nfev;
 for(int i=0;i<count+SAMPLES;i++)for(int k=0;k<4;k++)fitResult[5+i*4+k]=fit.jac[i][k];
 return fitResult.data();
}
const double* marker_finish(const double* v){
 predicted.fill(0);const double distance=std::exp(v[2]),c=std::cos(v[3]),s=std::sin(v[3]);int total=0,precision=0,recall=0,visible=0;
 for(int y=0;y<H;y++)for(int x=0;x<W;x++)if(insideROI(x,y)){Point q;if(rayCoordinates(x,y,q)){const double a=distance*(v[0]-q[0]),b=distance*(v[1]-q[1]),u=std::abs(c*a+s*b),w=std::abs(-s*a+c*b),max=std::max(u,w);predicted[y*W+x]=(max<=.13&&max>=.123)||(u<=.005&&w<=.085)||(w<=.005&&u<=.085);total+=predicted[y*W+x];}}
 for(int y=0;y<H;y++)for(int x=0;x<W;x++){if(mask[y*W+x]&&dilated(predicted,x,y))precision++;if(predicted[y*W+x]&&dilated(mask,x,y))recall++;}
 for(const auto& point:samples){Point q={v[0]-(c*point[0]-s*point[1])/distance,v[1]-(s*point[0]+c*point[1])/distance};visible+=templateInside(q);}
 double ray[3];for(int i=0;i<3;i++)ray[i]=parameters[9+i]+v[0]*parameters[12+i]+v[1]*parameters[15+i];double cam[3];for(int i=0;i<3;i++)cam[i]=parameters[i]*ray[0]+parameters[3+i]*ray[1]+parameters[6+i]*ray[2];
 const double hx=c*parameters[12]+s*parameters[15],hy=-(c*parameters[13]+s*parameters[16]);
 finishResult={double(precision)/std::max(1,paintCount),double(recall)/std::max(1,total),double(visible),320+parameters[21]*cam[0]/-cam[2],180-parameters[21]*cam[1]/-cam[2],parameters[18]-distance*ray[0],parameters[19]-distance*ray[1],parameters[20]-distance*ray[2],distance,std::atan2(hy,hx),v[3],double(paintCount),double(count)};
 return finishResult.data();
}
}
