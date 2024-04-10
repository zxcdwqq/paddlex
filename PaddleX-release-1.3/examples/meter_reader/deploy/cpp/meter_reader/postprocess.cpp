// Copyright (c) 2020 PaddlePaddle Authors. All Rights Reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.


#include <iostream>
#include <vector>
#include <utility>
#include <limits>
#include <cmath>
#include <chrono>  // NOLINT

#include <opencv2/opencv.hpp>
#include <opencv2/highgui.hpp>
#include <opencv2/core/core.hpp>

#include "meter_reader/global.h"
#include "meter_reader/postprocess.h"

using namespace std::chrono;  // NOLINT

// The size of inputting images (SEG_IMAGE_SIZE x SEG_IMAGE_SIZE) of
// the segmenter.
#define SEG_IMAGE_SIZE 512
// During the postprocess phase, annulus formed by the radius from
// 130 to 250 of a circular meter will be converted to a rectangle.
// So the height of the rectangle is 120.
#define LINE_HEIGHT 120
// The width of the rectangle is 1570, that is to say the perimeter
// of a circular meter.
#define LINE_WIDTH 1570
// Radius of a circular meter
#define CIRCLE_RADIUS 250

const float pi = 3.1415926536f;
// Center of a circular meter
const int circle_center[] = {256, 256};


void creat_line_image(const std::vector<int64_t> &seg_image,
                      std::vector<unsigned char> *output) {
  float theta;
  int rho;
  int image_x;
  int image_y;

  // The minimum scale value is at the bottom left, the maximum scale value
  // is at the bottom right, so the vertical down axis is the starting axis and
  // rotates around the meter ceneter counterclockwise.
  for (int row = 0; row < LINE_HEIGHT; row++) {
    for (int col = 0; col < LINE_WIDTH; col++) {
      theta = pi * 2 / LINE_WIDTH * (col + 1);
      rho = CIRCLE_RADIUS - row - 1;
      image_y = static_cast<int>(circle_center[0] + rho * cos(theta) + 0.5);
      image_x = static_cast<int>(circle_center[1] - rho * sin(theta) + 0.5);
      (*output)[row * LINE_WIDTH + col] =
        seg_image[image_y * SEG_IMAGE_SIZE + image_x];
    }
  }

  return;
}

void convert_1D_data(const std::vector<unsigned char> &line_image,
                     std::vector<unsigned int> *scale_data,
                     std::vector<unsigned int> *pointer_data) {
  // Accumulte the number of positions whose label is 1 along the height axis.
  // Accumulte the number of positions whose label is 2 along the height axis.
  for (int col = 0; col < LINE_WIDTH; col++) {
    (*scale_data)[col] = 0;
    (*pointer_data)[col] = 0;
    for (int row = 0; row < LINE_HEIGHT; row++) {
        if (line_image[row * LINE_WIDTH + col] == 1) {
            (*pointer_data)[col]++;
        } else if (line_image[row * LINE_WIDTH + col] == 2) {
            (*scale_data)[col]++;
        }
    }
  }
  return;
}

void scale_mean_filtration(const std::vector<unsigned int> &scale_data,
                           std::vector<unsigned int> *scale_mean_data) {
  int sum = 0;
  float mean = 0;
  int size = scale_data.size();
  for (int i = 0; i < size; i++) {
      sum = sum + scale_data[i];
  }
  mean = static_cast<float>(sum) / static_cast<float>(size);

  for (int i = 0; i < size; i++) {
    if (static_cast<float>(scale_data[i]) >= mean) {
        (*scale_mean_data)[i] = scale_data[i];
    }
  }

  return;
}

void get_meter_reader(const std::vector<unsigned int> &scale,
                      const std::vector<unsigned int> &pointer,
                      READ_RESULT *result) {
  std::vector<float> scale_location;
  float one_scale_location = 0;
  bool scale_flag = 0;
  unsigned int one_scale_start = 0;
  unsigned int one_scale_end = 0;

  float pointer_location = 0;
  bool pointer_flag = 0;
  unsigned int one_pointer_start = 0;
  unsigned int one_pointer_end = 0;

  for (int i = 0; i < LINE_WIDTH; i++) {
    // scale location
    if (scale[i] > 0 && scale[i+1] > 0) {
      if (scale_flag == 0) {
        one_scale_start = i;
        scale_flag = 1;
      }
    }
    if (scale_flag == 1) {
      if (scale[i] == 0 && scale[i+1] == 0) {
          one_scale_end = i - 1;
          one_scale_location = (one_scale_start + one_scale_end) / 2.;
          scale_location.push_back(one_scale_location);
          one_scale_start = 0;
          one_scale_end = 0;
          scale_flag = 0;
      }
    }

    // pointer location
    if (pointer[i] > 0 && pointer[i+1] > 0) {
      if (pointer_flag == 0) {
        one_pointer_start = i;
        pointer_flag = 1;
      }
    }
    if (pointer_flag == 1) {
      if ((pointer[i] == 0) && (pointer[i+1] == 0)) {
        one_pointer_end = i - 1;
        pointer_location = (one_pointer_start + one_pointer_end) / 2.;
        one_pointer_start = 0;
        one_pointer_end = 0;
        pointer_flag = 0;
      }
    }
  }

  int scale_num = scale_location.size();
  result->scale_num = scale_num;
  result->scales = -1;
  result->ratio = -1;
  if (scale_num > 0) {
    for (int i = 0; i < scale_num - 1; i++) {
      if (scale_location[i] <= pointer_location &&
            pointer_location < scale_location[i + 1]) {
        result->scales = i + 1 +
          (pointer_location-scale_location[i]) /
          (scale_location[i+1]-scale_location[i] + 1e-05);
      }
    }
    result->ratio =
      (pointer_location - scale_location[0]) /
      (scale_location[scale_num - 1] - scale_location[0] + 1e-05);
  }
  return;
}

void read_process(const std::vector<std::vector<int64_t>> &seg_image,
                  std::vector<READ_RESULT> *read_results,
                  const int thread_num) {
    int read_num = seg_image.size();
    #pragma omp parallel for num_threads(thread_num)
    for (int i_read = 0; i_read < read_num; i_read++) {
        // Convert the circular meter into a rectangular meter
        std::vector<unsigned char> line_result(LINE_WIDTH*LINE_HEIGHT, 0);
        creat_line_image(seg_image[i_read], &line_result);

        // Get two one-dimension data where 0 represents background and
        // >0 represents a scale or a pointer
        std::vector<unsigned int> scale_data(LINE_WIDTH);
        std::vector<unsigned int> pointer_data(LINE_WIDTH);
        convert_1D_data(line_result, &scale_data, &pointer_data);
        // Fliter scale data whose value is lower than the mean value
        std::vector<unsigned int> scale_mean_data(LINE_WIDTH);
        scale_mean_filtration(scale_data, &scale_mean_data);

        // Get the number of scales，the pointer location relative to the
        // scales, the ratio between the distance from the pointer to the
        // starting scale and distance from the ending scale to the
        // starting scale.
        READ_RESULT result;
        get_meter_reader(scale_mean_data, pointer_data, &result);

        (*read_results)[i_read] = std::move(result);
    }
    return;
}
