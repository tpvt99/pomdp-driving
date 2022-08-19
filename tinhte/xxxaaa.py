#!/home/cunjun/p3_catkin_ws/ros3.6/bin/python

import logging
import sys
MAX_HISTORY_MOTION_PREDICTION = 30 # This value is same in moped_param.h
import numpy as np

logging.basicConfig(filename="/home/cunjun/p3_catkin_ws/src/tinhte/logfile.txt",
                    filemode='w',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S',
                    level=logging.DEBUG)

# Should not use this as this won't work because of different parameters
# def call_constant_velocity():
#     cv = ConstantVelocity()
#
#     observation_trajectories = np.random.rand(5, 10, 2)
#     predictions = cv.get_multi_predictions(observation_trajectories, pred_len=7, avg_point_list=(2,))
#     print(predictions)

def call(agentDict):
    # Step 1. Write dictionary to a file
    logging.info("Receive info")
    logging.info(sys.executable)
    try:
        import pickle
        logging.info("Can import pickle")
        logging.info(pickle)
    except:
        logging.info("Cannot import pickle. Error")

    import pickle
    with open("agentDict.pickle", "wb") as file:
         pickle.dump(agentDict, file, pickle.HIGHEST_PROTOCOL)
    logging.info("Dumping info")

    try:
        import numpy as np
        logging.info("Can import numpy")
        logging.info(np)
    except:
        logging.info("Cannot import numpy. Error")

    import numpy as np

    xy_pos_list = []
    for agentID, agentInfo in agentDict.items():
        x_pos = np.array(agentInfo["x"])
        y_pos = np.array(agentInfo["y"])
        logging.info(f"Shape of x_pos is {x_pos.shape} and y_pos is {y_pos.shape}")
        xy_pos = np.concatenate([x_pos[..., np.newaxis], y_pos[..., np.newaxis]], axis=1)  # shape (n,2)
        # first axis, we pad width=0 at beginning and pad width=MAX_HISTORY_MOTION_PREDICTION-xy_pos.shape[0] at the end
        # second axis (which is x and y axis), we do not pad anything as it does not make sense to pad anything
        xy_pos = np.pad(xy_pos, pad_width=((0, MAX_HISTORY_MOTION_PREDICTION - xy_pos.shape[0]), (0, 0)), mode="edge")
        xy_pos_list.append(xy_pos)
    agents_history = np.stack(xy_pos_list)

    logging.info(agents_history)
