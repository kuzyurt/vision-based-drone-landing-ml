(() => {
  const ops=window.__app?.flightOps,bridge=ops?.bridge,state=ops?.state;
  return {state: state ? {ready:state.ready,error:state.error,drone:state.drone,ml:state.ml,radio:state.radio?{enabled:state.radio.enabled,connected:state.radio.connected,status:state.radio.status}:null} : null,
    cameraView:!!bridge?.cameraView,installed:!!bridge?.installed,holding:ops?._holding,started:ops?._started,policy:bridge?.policy?.status};
})()
