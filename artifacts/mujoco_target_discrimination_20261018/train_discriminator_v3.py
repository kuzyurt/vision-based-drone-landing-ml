"""Specific import-package repair; reuse completed v2 images without recollection."""
import sys,types
import train_discriminator as frozen_v2

original_prepare=frozen_v2.prepare
def prepare(manifest,out,runtime):
    # __package__ belongs to the imported module, not a runtime instance.
    module=sys.modules[type(runtime).__module__]
    facade=types.SimpleNamespace(__package__=module.__package__,model=runtime.model)
    return original_prepare(manifest,out,facade)
frozen_v2.prepare=prepare

if __name__=='__main__':frozen_v2.main()
