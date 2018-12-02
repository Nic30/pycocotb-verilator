#pragma once

#include <Python.h>
#include <vector>
#include <unordered_set>

/*
 * Proxy for memory of signal in simulation. Allows r/w access from python and value change detection.
 * */
struct SignalMemProxy_t {
    PyObject_HEAD
	bool is_read_only; // flag which tells if this signal can be written
	uint8_t * signal; // pointer to memory where signal value is stored in simulator
	size_t signal_size; // byte size of value
	bool is_signed; // flag for value of signed type
	std::vector<PyObject *> * callbacks; // python functions which are called when value of this signal changes
	std::unordered_set<SignalMemProxy_t*> * signals_checked_for_change; // set of signals which are checked for change after each step
	uint8_t * value_cache; // buffer to store previous value for event detection

	// properties used for simplified associations and debug in python
	PyObject * name; // physical name
	PyObject * _name; // logical name
	PyObject * _dtype; // type notation for python
	PyObject * _origin; // signal object which this proxy substitutes
	PyObject * _ag; // simulation agent which drive or monitor this signal
};

/*
 * Initialize SignalMemProxy_t
 * */
void SignalMemProxy_c_init(SignalMemProxy_t * self, bool is_read_only,
		uint8_t * signal, size_t signal_size, bool is_signed, const char * name,
		std::unordered_set<SignalMemProxy_t*> * signals_checked_for_change);

/*
 * Store actual value for later change detection
 * */
void SignalMemProxy_cache_value(SignalMemProxy_t* self);

/*
 * Evaluate if value changed
 * @note SignalMemProxy_cache_value has to be called first
 * */
bool SignalMemProxy_value_changed(SignalMemProxy_t* self);

extern PyTypeObject SignalMemProxy_pytype;
