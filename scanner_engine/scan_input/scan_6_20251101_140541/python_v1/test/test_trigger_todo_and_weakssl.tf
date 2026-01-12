# This Terraform file is designed to trigger:
# - The 'track_uses_of_todo_tags' rule (by using a TODO tag in a resource)
# - The 'weak_ssltls_protocols_should_not_be_used' rule (by specifying a weak protocol)

resource "aws_security_group" "example" {
  name        = "example"
  description = "TODO: This needs to be reviewed for security."
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_lb_listener" "bad_ssl" {
  load_balancer_arn = "arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/my-load-balancer/50dc6c495c0c9188"
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2015-05" # weak SSL/TLS policy
  certificate_arn   = "arn:aws:acm:us-west-2:123456789012:certificate/12345678-1234-1234-1234-123456789012"
}

resource "aws_lb_listener" "bad_example" {
  protocol   = "TLS"
  ssl_policy = "ELBSecurityPolicy-TLS-1-0-2015-04"
}
