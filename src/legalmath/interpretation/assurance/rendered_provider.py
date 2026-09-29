"""Fresh bounded model context with an explicitly retained public source image."""
from pathlib import Path
from ...canonical import raw_digest
from ...errors import LegalMathError
from ..search.providers import CodexProvider,Completion
from .grants import GrantedAllowance


class RenderedSourceProvider(CodexProvider):
    provider_id='codex.rendered-source.v1'

    def __init__(self,*,allowance,image,sha256):
        if not isinstance(allowance,GrantedAllowance):raise LegalMathError('E_AUTHORITY')
        super().__init__(allowance=allowance)
        self.image=Path(image).resolve();self.image_hash=sha256
        self._check()

    def _check(self):
        if (self.image.suffix.lower()!='.png' or self.image.stat().st_size>8*1024*1024 or
                raw_digest(self.image.read_bytes())!=self.image_hash):
            raise LegalMathError('E_INTEGRITY',details='Rendered source image changed or exceeds its explicit profile')

    def command(self,directory,schema,output):
        self._check()
        return super().command(directory,schema,output)[:-1]+['--image',str(self.image),'--','-']

    def complete(self,request,schema,settings):
        self._check()
        wire={**request,'attached_rendered_source':{'sha256':self.image_hash,'media_type':'image/png'}}
        answer=super().complete(wire,schema,settings)
        self._check()
        return Completion(answer.value,{**answer.provenance,'rendered_source_sha256':self.image_hash,
            'independence':'PIXEL_INPUT_AND_TEXT_METHODS; SAME_MODEL_CORRELATION_UNMEASURED'})
