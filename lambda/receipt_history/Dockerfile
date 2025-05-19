FROM public.ecr.aws/lambda/python:3.9

# Copy function code
COPY receipt_history.py ${LAMBDA_TASK_ROOT}

# Install dependencies to LAMBDA_TASK_ROOT
COPY requirements.txt .
RUN pip install -r requirements.txt --target "${LAMBDA_TASK_ROOT}"

# Set the CMD to your handler (entrypoint)
CMD ["receipt_history.lambda_handler"]