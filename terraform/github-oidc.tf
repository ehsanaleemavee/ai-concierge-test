# Lets GitHub Actions deploy WITHOUT storing AWS keys in GitHub.
# GitHub proves who it is with a short-lived token; this role trusts only
# your repo's main branch. Terraform creates it for you during apply.
resource "aws_iam_openid_connect_provider" "github" {
  count           = var.enable_github_oidc ? 1 : 0
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

data "aws_iam_policy_document" "github_trust" {
  count = var.enable_github_oidc ? 1 : 0
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github[0].arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      # GitHub now sends "repo:owner@<id>/name@<id>:..." (with numeric IDs); accept both formats.
      values = [
        "repo:${var.github_repo}:ref:refs/heads/main",
        "repo:${split("/", var.github_repo)[0]}@*/${split("/", var.github_repo)[1]}@*:ref:refs/heads/main",
      ]
    }
  }
}

resource "aws_iam_role" "github_deploy" {
  count              = var.enable_github_oidc ? 1 : 0
  name               = "${local.name}-github-deploy"
  assume_role_policy = data.aws_iam_policy_document.github_trust[0].json
}

resource "aws_iam_role_policy" "github_deploy" {
  count = var.enable_github_oidc ? 1 : 0
  name  = "deploy"
  role  = aws_iam_role.github_deploy[0].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      { Effect = "Allow", Action = ["ecr:GetAuthorizationToken"], Resource = "*" },
      {
        Effect = "Allow"
        Action = ["ecr:BatchCheckLayerAvailability", "ecr:InitiateLayerUpload", "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload", "ecr:PutImage", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer"]
        Resource = [for r in aws_ecr_repository.svc : r.arn]
      },
      {
        Effect   = "Allow"
        Action   = ["ecs:DescribeTaskDefinition", "ecs:RegisterTaskDefinition", "ecs:DescribeServices", "ecs:UpdateService"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = [aws_iam_role.execution.arn, aws_iam_role.task.arn]
      },
    ]
  })
}
