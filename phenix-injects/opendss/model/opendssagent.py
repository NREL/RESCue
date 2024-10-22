import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

from opendss_wrapper import OpenDSS
import helics as h
import json


def publish_item_measurements(items, fed, feeder, element_type='Line'):
    # gather item measurements
    for item in items:
        try:
            voltage = feeder.get_voltage(item, element_type, average=True)
        except:
            voltage = 0.0
        try:
            current = feeder.get_current(item, element_type, total=True)
        except:
            current = 0.0
        try:
            active_power, reactive_power = feeder.get_power(item, element_type, total=True)
        except:
            active_power= 0.0
            reactive_power = 0.0

        print(f' Item {item}: vtg {voltage} cur {current} p {active_power}')
        h.helicsPublicationPublishDouble(h.helicsFederateGetPublication(
            fed, f'opendss/{item}.voltage'), voltage)
        h.helicsPublicationPublishDouble(h.helicsFederateGetPublication(
            fed, f'opendss/{item}.current'), current)
        if element_type == 'Line':
            status = feeder.get_is_open(item, element=element_type)
            h.helicsPublicationPublishDouble(h.helicsFederateGetPublication(
                fed, f'opendss/{item}.power'), active_power)
            h.helicsPublicationPublishDouble(
                h.helicsFederateGetPublication(fed, f'opendss/{item}.status'), status)
            h.helicsPublicationPublishDouble(h.helicsFederateGetPublication(
                fed, f'opendss/{item}.freq'), 1)
        elif element_type == 'Storage':
            soc = feeder.get_property(item, '%stored', element='Storage')
            h.helicsPublicationPublishDouble(h.helicsFederateGetPublication(
                fed, f'opendss/{item}.active_power'), active_power)
            h.helicsPublicationPublishDouble(h.helicsFederateGetPublication(
                fed, f'opendss/{item}.reactive_power'), reactive_power)
            h.helicsPublicationPublishDouble(
                h.helicsFederateGetPublication(fed, f'opendss/{item}.soc'), soc/100)


def endpoint_otsim_updates(fed, breakers, feeder):
    # ot sim endpoint message processing
    ot_sim_endpoint = h.helicsFederateGetEndpoint(fed, 'updates')
    if h.helicsEndpointHasMessage(ot_sim_endpoint):
        controls = h.helicsEndpointGetMessage(ot_sim_endpoint)
        if h.helicsMessageIsValid(controls):
            all_controls = json.loads(h.helicsMessageGetString(controls))
            if all_controls and len(all_controls) > 0:
                print("all_controls=", all_controls)
                print("all_controls type=", type(all_controls))
                name, attri = all_controls[0].get('tag', '').split('.')
                if name in breakers:
                    feeder.set_is_open(name, open=all_controls[0].get(
                        'value', ''), element='Line')
                    print("Name is",name)
                else:
                    print(f"Device {name} not in breakerlist {breakers}")
    else:
        print("No msg from endpoint")


if __name__ == "__main__":
    # Timing variables
    load_dotenv()

    time_resolution = timedelta(minutes=1)
    start_time = datetime.now()
    experiment_duration = int(os.environ.get('EXPERIMENT_DURATION', 60))
    end_time = start_time + timedelta()
    feeder = OpenDSS(os.path.join(os.environ.get('INPUTS_PATH','.'),'master.dss'),
                     timedelta(minutes=1), start_time)

    breakers = [
        "671692",
        "breaker680"
    ]
    storages = [
        "battery_680",
        "battery_680b"
    ]

    # helics
    fed = h.helicsCreateCombinationFederateFromConfig(
        os.environ.get('CONFIG_PATH', "fed_config.json"))
    h.helicsFederateEnterExecutingMode(fed)

    req_time = start_time.second
    while req_time < experiment_duration:
        grantedtime = h.helicsFederateRequestTime(fed, req_time)
        endpoint_otsim_updates(fed, breakers, feeder)
        # run power flow simulation
        feeder.run_dss()
        # gather breaker measurements
        publish_item_measurements(breakers, fed, feeder, 'Line')
        publish_item_measurements(storages, fed, feeder, 'Storage')
        req_time = grantedtime + 1
