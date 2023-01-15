from ipykernel.kernelapp import IPKernelApp
from . import JoernKernel

IPKernelApp.launch_instance(kernel_class=JoernKernel)
