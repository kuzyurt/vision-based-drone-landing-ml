// FP64 bounded TRF with the reference soft_l1 loss and stopping rules.
// Four columns permit a small one-sided Jacobi SVD without Python dispatch.
// Algorithm port of scipy/optimize/_lsq/{trf,common}.py (SciPy 1.18.0).
// SciPy copyright and BSD terms: SCIPY-LICENSE.txt.
namespace trf {
using V=std::array<double,4>;
using M=std::array<V,4>;
double dot4(const V&a,const V&b){double r=0;for(int i=0;i<4;i++)r+=a[i]*b[i];return r;}
double norm(const V&a){return std::sqrt(dot4(a,a));}
V mul(const V&a,const V&b){V r;for(int i=0;i<4;i++)r[i]=a[i]*b[i];return r;}
V scale(V a,double t){for(double&v:a)v*=t;return a;}
V add(V a,const V&b){for(int i=0;i<4;i++)a[i]+=b[i];return a;}
V mat(const M&a,const V&b){V r{};for(int i=0;i<4;i++)r[i]=dot4(a[i],b);return r;}
void svd(std::vector<V> a,V&s,M&v){
 v={};for(int i=0;i<4;i++)v[i][i]=1;
 for(int sweep=0;sweep<64;sweep++){
  bool changed=false;
  for(int p=0;p<3;p++)for(int q=p+1;q<4;q++){
   double aa=0,bb=0,ab=0;for(const auto&r:a){aa+=r[p]*r[p];bb+=r[q]*r[q];ab+=r[p]*r[q];}
   if(std::abs(ab)<=std::numeric_limits<double>::epsilon()*std::sqrt(aa*bb))continue;
   changed=true;double z=(bb-aa)/(2*ab),t=std::copysign(1.,z)/(std::abs(z)+std::hypot(1.,z)),c=1/std::sqrt(1+t*t),sn=c*t;
   for(auto&r:a){double x=r[p],y=r[q];r[p]=c*x-sn*y;r[q]=sn*x+c*y;}
   for(auto&r:v){double x=r[p],y=r[q];r[p]=c*x-sn*y;r[q]=sn*x+c*y;}
  }
  if(!changed)break;
 }
 for(int j=0;j<4;j++){s[j]=0;for(const auto&r:a)s[j]+=r[j]*r[j];s[j]=std::sqrt(s[j]);}
 for(int i=0;i<3;i++)for(int j=i+1;j<4;j++)if(s[j]>s[i]){std::swap(s[j],s[i]);for(auto&r:v)std::swap(r[j],r[i]);}
}
double cost(const std::vector<double>&f){double c=0;for(double x:f)c+=2.25*(std::sqrt(1+x*x/2.25)-1);return c;}
void robust(std::vector<V>&j,std::vector<double>&f){for(size_t i=0;i<f.size();i++){double z=1+f[i]*f[i]/2.25,r1=1/std::sqrt(z),r2=-.5*r1/z/2.25,k=std::sqrt(std::max(std::numeric_limits<double>::epsilon(),r1+2*r2*f[i]*f[i]));for(double&x:j[i])x*=k;f[i]*=r1/k;}}
V grad(const std::vector<V>&j,const std::vector<double>&f){V g{};for(size_t i=0;i<j.size();i++)for(int k=0;k<4;k++)g[k]+=j[i][k]*f[i];return g;}
V cl(const V&x,const V&g,const V&lo,const V&hi,V&dv){V v;for(int i=0;i<4;i++){v[i]=g[i]<0?hi[i]-x[i]:g[i]>0?x[i]-lo[i]:1;dv[i]=g[i]<0?-1:g[i]>0?1:0;}return v;}
V trust(const V&s,const M&v,const V&g,double delta,double&alpha,int m){
 V suf{};for(int i=0;i<4;i++)for(int k=0;k<4;k++)suf[i]+=v[k][i]*g[k];
 bool full=s[3]>std::numeric_limits<double>::epsilon()*m*s[0];
 auto step=[&](double a){V t;for(int i=0;i<4;i++)t[i]=-suf[i]/(s[i]*s[i]+a);return mat(v,t);};
 if(full){V p=step(0);if(norm(p)<=delta){alpha=0;return p;}}
 auto phi=[&](double a){double n=0,der=0;for(int i=0;i<4;i++){double d=s[i]*s[i]+a;n+=suf[i]*suf[i]/(d*d);der-=suf[i]*suf[i]/(d*d*d);}n=std::sqrt(n);return std::array<double,2>{n-delta,der/n};};
 double upper=norm(suf)/delta,lower=0;if(full){auto p=phi(0);lower=-p[0]/p[1];}
 if(!full&&alpha==0)alpha=std::max(.001*upper,std::sqrt(lower*upper));
 for(int it=0;it<10;it++){if(alpha<lower||alpha>upper)alpha=std::max(.001*upper,std::sqrt(lower*upper));auto p=phi(alpha);if(p[0]<0)upper=alpha;double r=p[0]/p[1];lower=std::max(lower,alpha-r);alpha-=(p[0]+delta)*r/delta;if(std::abs(p[0])<.01*delta)break;}
 V p=step(alpha);return scale(p,delta/norm(p));
}
double bound(const V&x,const V&s,const V&lo,const V&hi,V*hits=nullptr){V steps;double t=std::numeric_limits<double>::infinity();for(int i=0;i<4;i++){steps[i]=s[i]==0?std::numeric_limits<double>::infinity():std::max((lo[i]-x[i])/s[i],(hi[i]-x[i])/s[i]);t=std::min(t,steps[i]);}if(hits)for(int i=0;i<4;i++)(*hits)[i]=steps[i]==t?(s[i]>0?1:-1):0;return t;}
double intersect(const V&x,const V&s,double delta){double a=dot4(s,s),b=dot4(x,s),c=dot4(x,x)-delta*delta,q=-(b+std::copysign(std::sqrt(std::max(0.,b*b-a*c)),b));return std::max(q/a,c/q);}
M hessian(const std::vector<V>&j,const V&diag){M h{};for(const auto&r:j)for(int a=0;a<4;a++)for(int b=0;b<4;b++)h[a][b]+=r[a]*r[b];for(int a=0;a<4;a++)h[a][a]+=diag[a];return h;}
double quad(const M&h,const V&g,const V&s){return .5*dot4(s,mat(h,s))+dot4(s,g);}
std::array<double,2> minquad(double a,double b,double c,double lo,double hi){double t=lo,val=lo*(a*lo+b)+c;auto check=[&](double x){double y=x*(a*x+b)+c;if(y<val){val=y;t=x;}};check(hi);if(a!=0){double ex=-.5*b/a;if(ex>lo&&ex<hi)check(ex);}return {t,val};}
struct Step{V x,hat;double prediction;};
Step select(const V&x,const M&h,const V&g,V ph,const V&d,double delta,const V&lo,const V&hi,double theta){
 V p=mul(d,ph);bool inside=true;for(int i=0;i<4;i++)inside&=x[i]+p[i]>=lo[i]&&x[i]+p[i]<=hi[i];if(inside)return {p,ph,-quad(h,g,ph)};
 V hits;double stride=bound(x,p,lo,hi,&hits);V rh=ph;for(int i=0;i<4;i++)if(hits[i]!=0)rh[i]*=-1;V r=mul(d,rh);p=scale(p,stride);ph=scale(ph,stride);
 double totr=intersect(ph,rh,delta),tobound=bound(add(x,p),r,lo,hi),rs=std::min(totr,tobound),rl=rs>0?(1-theta)*stride/rs:0,ru=rs>0?(rs==tobound?theta*tobound:totr):-1,rv=std::numeric_limits<double>::infinity();
 if(rl<=ru){auto q=minquad(.5*dot4(rh,mat(h,rh)),dot4(g,rh)+dot4(ph,mat(h,rh)),quad(h,g,ph),rl,ru);rv=q[1];rh=add(ph,scale(rh,q[0]));r=mul(d,rh);}
 p=scale(p,theta);ph=scale(ph,theta);double pv=quad(h,g,ph);
 V ah=scale(g,-1),a=mul(d,ah);totr=delta/norm(ah);tobound=bound(x,a,lo,hi);double as=tobound<totr?theta*tobound:totr;auto aq=minquad(.5*dot4(ah,mat(h,ah)),dot4(g,ah),0,0,as);ah=scale(ah,aq[0]);a=scale(a,aq[0]);
 if(pv<rv&&pv<aq[1])return {p,ph,-pv};if(rv<pv&&rv<aq[1])return {r,rh,-rv};return {a,ah,-aq[1]};
}
struct Fit{V x;std::vector<V> jac;int nfev;};
template<class Residual,class Jacobian> Fit solve(V x,const V&lo,const V&hi,int m,Residual residual,Jacobian jacobian){
 auto f=residual(x);auto j=jacobian(x);double c=cost(f);robust(j,f);V g=grad(j,f),dv,v=cl(x,g,lo,hi,dv),scaled;for(int i=0;i<4;i++)scaled[i]=x[i]/std::sqrt(v[i]);double delta=norm(scaled);if(delta==0)delta=1;double alpha=0;int nfev=1;bool terminated=false;
 while(true){v=cl(x,g,lo,hi,dv);double gn=0;for(int i=0;i<4;i++)gn=std::max(gn,std::abs(g[i]*v[i]));if(gn<1e-8||terminated||nfev==35)break;
  V d,diag;for(int i=0;i<4;i++){d[i]=std::sqrt(v[i]);diag[i]=g[i]*dv[i];}V gh=mul(d,g);auto jh=j;for(auto&r:jh)r=mul(r,d);auto aug=jh;for(int i=0;i<4;i++){V r{};r[i]=std::sqrt(diag[i]);aug.push_back(r);}V s;M vectors;svd(aug,s,vectors);M h=hessian(jh,diag);double actual=-1,cnew=c;V xnew=x;std::vector<double> fnew;
  while(actual<=0&&nfev<35){V ph=trust(s,vectors,gh,delta,alpha,m);auto step=select(x,h,gh,ph,d,delta,lo,hi,std::max(.995,1-gn));xnew=add(x,step.x);for(int i=0;i<4;i++){if(xnew[i]<=lo[i])xnew[i]=std::nextafter(lo[i],hi[i]);if(xnew[i]>=hi[i])xnew[i]=std::nextafter(hi[i],lo[i]);if(xnew[i]<lo[i]||xnew[i]>hi[i])xnew[i]=.5*(lo[i]+hi[i]);}
   fnew=residual(xnew);nfev++;double hn=norm(step.hat);bool finite=true;for(double z:fnew)finite&=std::isfinite(z);if(!finite){delta=.25*hn;continue;}cnew=cost(fnew);actual=c-cnew;double ratio=step.prediction>0?actual/step.prediction:step.prediction==0&&actual==0?1:0;double nd=ratio<.25?.25*hn:ratio>.75&&hn>.95*delta?2*delta:delta;
   terminated=(actual<1e-8*c&&ratio>.25)||norm(step.x)<1e-8*(1e-8+norm(x));if(terminated)break;alpha*=delta/nd;delta=nd;
  }
  if(actual>0){x=xnew;f=fnew;c=cnew;j=jacobian(x);robust(j,f);g=grad(j,f);}
 }
 return {x,j,nfev};
}
}
