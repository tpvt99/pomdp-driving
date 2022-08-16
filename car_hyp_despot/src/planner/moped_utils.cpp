#include <Python.h>
#include "state.h"
#include "coord.h"
#include "moped_utils.h"

namespace MopedUtils {

    PyObject * buildAgentList(std::vector<AgentStruct> neighborAgents) {
        //PyGILState_STATE gstate = PyGILState_Ensure();
        PyObject * agentDict = PyDict_New();

        cout << "[Phong] buildAgentList: " << endl;

        if (!agentDict) {
            cout << "Unable to allocate memory for Python dict" << endl;
            throw logic_error("Unable to allocate memory for Python dict");
        }

        for (const AgentStruct &tempAgent : neighborAgents) {
            std::vector<COORD> hist = tempAgent.coordHistory.coord_history;
            PyObject * listx = PyList_New(hist.size());
            if (!listx) {
                cout << "Unable to allocate memory for Python list" << endl;
                Py_DECREF(listx);
                throw logic_error("Unable to allocate memory for Python list");
            }
            PyObject *listy = PyList_New(hist.size());
            if (!listy) {
                Py_DECREF(listy);
                throw logic_error("Unable to allocate memory for Python list");
            }

            for (unsigned int i = 0; i < hist.size(); i++) {
                PyObject *x_pos = PyFloat_FromDouble(hist[i].x);
                if (!x_pos) {
                    Py_DECREF(listx);
                    Py_DECREF(listy);
                    Py_DECREF(x_pos);
                    throw logic_error("Unable to allocated memory for python x.pos");
                }
                PyObject *y_pos = PyFloat_FromDouble(hist[i].y);
                if (!y_pos) {
                    Py_DECREF(listx);
                    Py_DECREF(listy);
                    Py_DECREF(y_pos);
                    throw logic_error("Unable to allocated memory for python y.pos");
                }
                PyList_SetItem(listx, i, x_pos);
                PyList_SetItem(listy, i, y_pos);

                //Py_DECREF(x_pos); No need to deref because _SetItem() does not increase
                //Py_DECREF(y_pos);
            }

            PyObject *agentType = PyLong_FromLong(tempAgent.type);
            PyObject *agentId = PyLong_FromLong(tempAgent.id);
            PyObject *info_dict = Py_BuildValue("{s:O,s:O,s:O}", "x", listx, "y", listy, "type", agentType);
            PyDict_SetItem(agentDict, agentId, info_dict);

            //Py_DECREF(agentType); no need because immutable type so won't decrease anyway
            //Py_DECREF(agentId);

            Py_DECREF(listx);
            Py_DECREF(listy);
            Py_DECREF(info_dict);

            cout << "[Phong] buildAgentList: after deref: agentType: " << agentType->ob_refcnt;
            cout << " listx " << listx->ob_refcnt;
            cout << " listy " << listy->ob_refcnt;
            cout << " info_dict " << info_dict->ob_refcnt;
            cout << " agentId " << agentId->ob_refcnt << endl;
        }

        cout << "[Phong] buildAgentList: with ref count: " << agentDict->ob_refcnt << endl;

        //PyGILState_Release(gstate);

        return agentDict;
    }

}
