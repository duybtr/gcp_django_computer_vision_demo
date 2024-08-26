# Pull base image
FROM python:3.12

# Set work directory
WORKDIR /code

# Install dependencies
COPY Pipfile Pipfile.lock /code/
RUN pip install pipenv && pipenv install --system

# Copy project
COPY . /code/

# Run the command
CMD ["python", "manage.py", "process_invoice"]