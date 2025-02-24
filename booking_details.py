
from pydantic import BaseModel, Field , field_validator, ValidationInfo , model_validator
from langgraph.graph.message import AnyMessage , add_messages
from langgraph.graph import StateGraph, MessagesState, START, END
import os
import requests
from langchain_openai import ChatOpenAI
from flask import Flask, request, jsonify
from datetime import datetime
from geo_coding import GeoCodingAPI
app = Flask(__name__)
llm = ChatOpenAI(temperature=0, model="gpt-4o-mini")

def getData_for_duckling(text, dims):
    url = 'http://localhost:8000/parse'
    data = {
        'locale': 'en_US',
        'text': text,
        'dims': dims,
        'tz': "Asia/Ho_Chi_Minh"
    }
    response = requests.post(url, data=data)
    if response.status_code == 200:
        json_response = response.json()
        # value = json_response[0]['value']['value']
        return json_response
    else:
        return f"Error: {response.status_code}"
class BookingCarDetails(BaseModel):
    """Details for the bookings car details"""
    name: str = Field(
        ...,
        description="The name of the person booking the ride. Do not autofill if not provided",
    )
    number_phone: str = Field(
        ...,
        description="The phone number of the user. Do not autofill if not provided",
    )
    email: str = Field(
        ...,
        description="The email of the user. Do not autofill if not provided",
    )
    pick_up_location: str = Field(
        ...,
        description="The location where the user will be picked up. This can be a full address or a specific location name. Do not autofill if not provided",
    )
    destination_location: str = Field(
        ...,
        description="The destination location for the ride. This can be a full address or a specific location name. Do not autofill if not provided"
    )
    pick_up_time: str = Field(
        ...,
        description="The time the user intends to be picked up. No format keeps the text related to time. Do not autofill if not provided"
    )
    flight_code: str = Field(
        # default= 'None',
        ...,
        description="Flight numbers, consisting of letters and numbers, usually start with the airline code (e.g. VN123, SQ318)."
    )
    passengers: int = Field(
        ...,
        description="The number of passengers that will be in the car. Do not autofill if not provided"
    )
    @field_validator('pick_up_location')
    @classmethod
    def validate_pickup(cls, value:str, info: ValidationInfo):
        geoCodingAPI = GeoCodingAPI()
        if value == '':
            return ''
        else :
            geoCoding_pickup = geoCodingAPI.get_geocoding(value)
            if geoCoding_pickup["status"] == "OK" :

                return geoCoding_pickup['results'][0]['formatted_address']
            else:
                raise ValueError(f"Invalid pick-up location: {value}")
            
    @field_validator('destination_location')
    @classmethod
    def validate_destination(cls, value : str, info: ValidationInfo):
        geoCodingAPI = GeoCodingAPI()
        if value == '':
            return ''
        else :
            geoCoding_destination = geoCodingAPI.get_geocoding(value)
            if geoCoding_destination["status"] == "OK":
                if geoCoding_destination['results'][0]['formatted_address'] == info.data['pick_up_location']:
                    raise ValueError(f"Invalid destination location: {value}")
                else:

                    return geoCoding_destination['results'][0]['formatted_address']
            else:
            
                raise ValueError(f"Invalid destination location: {value}")
    @field_validator('pick_up_time')
    @classmethod
    def validate_pick_up_time(cls, value : str):
        dimensions = ["time"]
        if value == '':
            return ''
        try:
            expected_format = "%Y-%m-%dT%H:%M:%S.%f%z"
            parsed_datetime = datetime.strptime(value, expected_format)
            return value
        except :
            data = getData_for_duckling(value,dimensions)
            if data and isinstance(data, list) and 'value' in data[0] and 'value' in data[0]['value']:
                return data[0]['value']['value']
            else:
                raise ValueError("Invalid time format")
         
chain = llm.with_structured_output(BookingCarDetails)
@app.route('/api/booking', methods=['POST'])
def chat():
    input_data = request.json
    if not input_data or 'messages' not in input_data:
        return jsonify({'error': 'Invalid input'}), 400
    messages = input_data.get('messages', [])
    if not messages or not isinstance(messages, list):
        return jsonify({'error': 'Invalid input, messages must be a non-empty list'}), 400# This gets the items in the queue
    list_responses = []
    for message in messages:   
        # request_queue.put((request_id, message))
        reponse = chain.invoke(message)
        list_responses.append(reponse.model_dump())
    response = {
        'responses': list_responses
    }
    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=6060, threaded=True,debug=True)