from __future__ import absolute_import, division, print_function

import argparse
import timeit

import torch

from pyro.ops.contract import ubersum

# from pyro.util import ignore_jit_warnings

_CACHE = {}


def jit_ubersum(equation, *operands, **kwargs):

    key = equation, kwargs['batch_dims']
    if key not in _CACHE:

        def _ubersum(*operands):
            return ubersum(equation, *operands, **kwargs)

        # with ignore_jit_warnings():
        fn = torch.jit.trace(_ubersum, operands, check_trace=False)
        _CACHE[key] = fn

    return _CACHE[key](*operands)


def time_ubersum(equation, *operands, **kwargs):
    iters = kwargs.pop('iters')
    jit_ubersum(equation, *operands, **kwargs)
    time = -timeit.default_timer()
    for i in range(iters):
        jit_ubersum(equation, *operands, **kwargs)
    time += timeit.default_timer()
    return time


def main(args):
    if args.cuda:
        torch.set_default_tensor_type('torch.cuda.FloatTensor')
    else:
        torch.set_default_tensor_type('torch.FloatTensor')

    equation = args.equation
    batch_dims = args.batch_dims
    inputs, outputs = equation.split('->')
    inputs = inputs.split(',')

    dim_size = args.dim_size
    times = {}
    for plate_size in reversed(range(1, 1 + args.max_plate_size)):
        operands = []
        for dims in inputs:
            shape = torch.Size([plate_size if d in batch_dims else dim_size
                                for d in dims])
            operands.append(torch.randn(shape))

        time = time_ubersum(equation, *operands, batch_dims=batch_dims, iters=args.iters)
        times[plate_size] = time

    for plate_size, time in sorted(times.items()):
        print('{}\t{}'.format(plate_size, time))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="ubersum profiler")
    parser.add_argument("-e", "--equation", default="a,abi,bcij,adj,deij->")
    parser.add_argument("-b", "--batch-dims", default="ij")
    parser.add_argument("-d", "--dim-size", default=32, type=int)
    parser.add_argument("-p", "--max-plate-size", default=32, type=int)
    parser.add_argument("-n", "--iters", default=100, type=int)
    parser.add_argument('--cuda', action='store_true')
    parser.add_argument('--jit', action='store_true')
    args = parser.parse_args()
    main(args)
