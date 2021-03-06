#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""
This is an example implementation of ALS for learning how to use Spark. Please refer to
pyspark.ml.recommendation.ALS for more conventional use.

This example requires numpy (http://www.numpy.org/)
"""
from __future__ import print_function

import sys
import math
import numpy as np
from numpy.random import rand
from numpy import matrix
from pyspark.sql import SparkSession

LAMBDA = 0.01   # regularization
np.random.seed(42)


def rmse(R, ms, us):
    diff = R - ms * us.T
    return np.sqrt(np.sum(np.power(diff, 2)) / (M * U))


def update(i, mat, ratings):
    uu = mat.shape[0]
    ff = mat.shape[1]

    XtX = mat.T * mat
    Xty = mat.T * ratings[i, :].T

    for j in range(ff):
        XtX[j, j] += LAMBDA * uu

    return np.linalg.solve(XtX, Xty)


if __name__ == "__main__":

    """
    Usage: als [M] [U] [F] [iterations] [partitions]"
    """

    print("""WARN: This is a naive implementation of ALS and is given as an
      example. Please use pyspark.ml.recommendation.ALS for more
      conventional use.""", file=sys.stderr)

    spark = SparkSession\
        .builder\
        .appName("PythonALS")\
        .getOrCreate()

    sc = spark.sparkContext


    data = open(sys.argv[1]).readlines() 
    M = int(sys.argv[2])
    U = int(sys.argv[3])
    F = int(sys.argv[4])
    ITERATIONS = int(sys.argv[5])
    partitions = int(sys.argv[6])
    output = open(sys.argv[7], "w")

    print("Running ALS with n=%d, m=%d, f=%d, iters=%d, partitions=%d\n" %
          (M, U, F, ITERATIONS, partitions))

    user = []
    movie = []
    rownum = len(data)
    mat = np.zeros(shape=(M, U))
    
    # initial mat
    for i in range(1, rownum):
        lines = data[i].split(',')
        user.append(int(lines[0]))
        movie.append(int(lines[1]))
    
    user = sorted(set(user))
    movie = sorted(set(movie))

    for i in range(1, rownum):
        lines = data[i].split(',')
        mat[user.index(int(lines[0]))][movie.index(int(lines[1]))] = float(lines[2])


    R = matrix(mat)
    ms = matrix(np.ones(shape=(M, F)))
    us = matrix(np.ones(shape=(U, F)))

    Rb = sc.broadcast(R)
    msb = sc.broadcast(ms)
    usb = sc.broadcast(us)

    for it in range(ITERATIONS):
        ms = sc.parallelize(range(M), partitions) \
               .map(lambda x: update(x, usb.value, Rb.value)) \
               .collect()
        # collect() returns a list, so array ends up being
        # a 3-d array, we take the first 2 dims for the matrix
        ms = matrix(np.array(ms)[:, :, 0])
        msb = sc.broadcast(ms)

        us = sc.parallelize(range(U), partitions) \
               .map(lambda x: update(x, msb.value, Rb.value.T)) \
               .collect()
        us = matrix(np.array(us)[:, :, 0])
        usb = sc.broadcast(us)

        error = rmse(R, ms, us)

        print("Iteration %d:" % it)
        print("\nRMSE: %5.4f\n" % error)
        output.write("%.4f\n" % error)

    spark.stop()
