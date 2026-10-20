aws ecr get-login-password --region ap-south-1 \
  | docker login \
    --username AWS \
    --password-stdin 804471951897.dkr.ecr.ap-south-1.amazonaws.com

docker tag chrion/careerhub-backend:1.0.0 \
  804471951897.dkr.ecr.ap-south-1.amazonaws.com/chrion/careerhub-backend:1.0.0

docker push \
  804471951897.dkr.ecr.ap-south-1.amazonaws.com/chrion/careerhub-backend:1.0.0