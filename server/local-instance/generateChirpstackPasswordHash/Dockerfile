FROM golang:1-alpine AS builder
WORKDIR /go/src/app
RUN go mod init
RUN go get "golang.org/x/crypto/pbkdf2"
RUN go get "github.com/pkg/errors"
COPY . .
#RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -a -o app .
RUN go build -a -o app .
ENV INPUT ""
CMD ./app $INPUT