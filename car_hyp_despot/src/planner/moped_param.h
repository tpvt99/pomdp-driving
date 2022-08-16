
#ifndef MOPEDPARAMS_H
#define MOPEDPARAMS_H

namespace MopedParams {
    const int MAX_HISTORY_MOTION_PREDICTION = 30;
    const bool PHONG_DEBUG = true; // to print my logging so that I can understand the logic
    const bool PHONG_DESPOT_DEBUG = true; // to print despot code so I understand pomdp planning
    const bool USE_MOPED = true; // true if using motion prediction instead of original code
}

#endif