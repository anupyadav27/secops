# Test file to trigger 5 rules

resource "aws_s3_bucket" "bad_bucket" {
  bucket = "my-bad-bucket"
  acl    = "private"
  # No logging block (should trigger S6258)
  versioning {
    enabled    = true
    mfa_delete = false # Should trigger S6255
  }
}

resource "aws_s3_bucket" "public_bucket" {
  bucket = "public-bucket"
  acl    = "public-read" # Should trigger S6281 (public ACL)
  versioning {
    enabled    = true
    mfa_delete = true
  }
}

resource "aws_db_instance" "unencrypted_db" {
  allocated_storage    = 20
  engine               = "mysql"
  instance_class       = "db.t2.micro"
  name                 = "mydb"
  username             = "foo"
  password             = "foobarbaz"
  parameter_group_name = "default.mysql5.7"
  # No storage_encrypted = true (should trigger S6303)
}

resource "aws_security_group" "open_sg" {
  name        = "open-sg"
  description = "Open to the world"
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Should trigger S6270 (public access)
  }
}
